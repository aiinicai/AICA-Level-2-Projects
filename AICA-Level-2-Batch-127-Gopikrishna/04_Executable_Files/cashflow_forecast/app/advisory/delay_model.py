"""Advisory collection-delay model (scikit-learn). It suggests dates only; the engine stays rule-based.

Training data: the uploaded payment history (invoice due date -> actual paid date).
Model: Ridge regression on the customer (one-hot) and log(amount), predicting days late.
Fallback to the due date when there is too little history overall (< MIN_ROWS), or for a customer
with fewer than MIN_PER_CUSTOMER past invoices. Predictions are clipped to 0..MAX_DELAY days.
Used only by scenarios with ``use_delay_model`` switched on; a re-date override always wins.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importers.specs import normalise_header
from app.models import CollectionHistory

MIN_ROWS, MIN_PER_CUSTOMER, MAX_DELAY = 30, 3, 180


@dataclass
class DelayModel:
    pipeline: object | None
    customers: dict[str, int]      # normalised customer -> history rows
    rows: int
    mae_days: float | None         # hold-out mean absolute error, for the screen

    def predict_days(self, customer: str, amount: float) -> tuple[int, str]:
        c = normalise_header(customer)
        if self.pipeline is None:
            return 0, "due date (not enough payment history)"
        if self.customers.get(c, 0) < MIN_PER_CUSTOMER:
            return 0, "due date (customer has little history)"
        import pandas as pd
        x = pd.DataFrame({"customer": [c], "log_amount": [np.log1p(max(amount, 0.0))]})
        days = int(round(float(np.clip(self.pipeline.predict(x)[0], 0, MAX_DELAY))))
        return days, f"model: about {days} days after due"


def fit(db: Session) -> DelayModel:
    import pandas as pd
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    hist = db.execute(select(CollectionHistory.customer, CollectionHistory.due_date, CollectionHistory.paid_date,
                             CollectionHistory.amount)).all()
    if not hist:
        return DelayModel(None, {}, 0, None)
    df = pd.DataFrame(hist, columns=["customer", "due", "paid", "amount"])
    df["customer"] = df["customer"].map(normalise_header)
    df["delay"] = [(p - d).days for p, d in zip(df["paid"], df["due"])]
    df["log_amount"] = np.log1p(df["amount"].astype(float).clip(lower=0))
    counts = df["customer"].value_counts().to_dict()
    if len(df) < MIN_ROWS:
        return DelayModel(None, counts, len(df), None)

    def make():
        return Pipeline([
            ("x", ColumnTransformer([("cust", OneHotEncoder(handle_unknown="ignore"), ["customer"]),
                                     ("amt", "passthrough", ["log_amount"])])),
            ("m", Ridge(alpha=1.0)),
        ])
    X, y = df[["customer", "log_amount"]], df["delay"].clip(lower=0, upper=MAX_DELAY)
    mae = None
    if len(df) >= 2 * MIN_ROWS:
        xtr, xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=0)
        p = make().fit(xtr, ytr)
        mae = float(np.mean(np.abs(np.clip(p.predict(xte), 0, MAX_DELAY) - yte)))
    return DelayModel(make().fit(X, y), counts, len(df), mae)


def predict_collection_dates(db: Session, items, as_of: date) -> dict[tuple[str, str], tuple[date, str]]:
    """(source, key) -> (suggested date, basis) for collection items. Only dates that change are returned."""
    model = fit(db)
    out = {}
    for it in items:
        days, basis = model.predict_days(it.counterparty, float(it.amount))
        if days:
            out[(it.source, it.key)] = (it.planned_date + timedelta(days=days), basis)
    return out
