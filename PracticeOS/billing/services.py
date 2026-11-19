"""Money logic. All amounts are Decimal and rounded half-up to paise; totals are always computed
here from line items, never taken from user input."""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.utils import fy_label

from .models import Invoice, InvoiceCounter, InvoiceItem, Payment, TimeEntry

PAISE = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(value).quantize(PAISE, rounding=ROUND_HALF_UP)


def compute_totals(items):
    """items: iterable of dicts with description, quantity, rate, tax_rate."""
    lines, subtotal, tax_total = [], Decimal("0"), Decimal("0")
    for it in items:
        amount = money(Decimal(it["quantity"]) * Decimal(it["rate"]))
        tax = money(amount * Decimal(it["tax_rate"]) / 100)
        lines.append({**it, "amount": amount, "tax": tax})
        subtotal += amount
        tax_total += tax
    return lines, money(subtotal), money(tax_total), money(subtotal + tax_total)


def _next_number(firm, issue_date) -> str:
    fy = fy_label(issue_date)
    counter, _ = InvoiceCounter.objects.select_for_update().get_or_create(firm=firm, fy=fy)
    counter.seq += 1
    counter.save(update_fields=["seq"])
    return f"INV/{fy}/{counter.seq:04d}"


@transaction.atomic
def create_invoice(*, firm, client, items, issue_date=None, due_date=None, notes="", time_entries=()) -> Invoice:
    items = list(items)
    if not items:
        raise ValidationError("An invoice needs at least one line item.")
    issue_date = issue_date or timezone.localdate()
    lines, subtotal, tax, total = compute_totals(items)
    invoice = Invoice.objects.create(
        firm=firm, client=client, number=_next_number(firm, issue_date), issue_date=issue_date,
        due_date=due_date or issue_date + timedelta(days=15), subtotal=subtotal, tax_amount=tax, total=total, notes=notes,
    )
    InvoiceItem.objects.bulk_create(
        InvoiceItem(invoice=invoice, description=l["description"], quantity=l["quantity"], rate=l["rate"], tax_rate=l["tax_rate"], amount=l["amount"])
        for l in lines
    )
    ids = [e.pk for e in time_entries]
    if ids:
        TimeEntry.objects.filter(firm=firm, pk__in=ids).update(invoice=invoice)
    return invoice


def items_from_time(entries, default_rate=Decimal("0"), tax_rate=Decimal("18")):
    out = []
    for e in entries.select_related("user", "task"):
        rate = e.hourly_rate if e.hourly_rate is not None else (e.user.hourly_rate if e.user.hourly_rate is not None else default_rate)
        what = e.task.title if e.task else (e.description or "Professional services")
        out.append({
            "description": f"{e.work_date:%Y-%m-%d} – {what} ({e.user.name})",
            "quantity": (Decimal(e.minutes) / 60).quantize(PAISE, rounding=ROUND_HALF_UP),
            "rate": rate, "tax_rate": tax_rate,
        })
    return out


@transaction.atomic
def record_payment(invoice: Invoice, *, amount, paid_on=None, method="", reference="") -> Payment:
    """Records a (part) payment; flips the invoice to PAID once it is fully settled."""
    invoice = Invoice.objects.select_for_update().prefetch_related("payments").get(pk=invoice.pk)
    amount = money(amount)
    if invoice.status == Invoice.Status.CANCELLED:
        raise ValidationError("Cancelled invoices cannot receive payments.")
    if amount <= 0:
        raise ValidationError("Amount must be greater than zero.")
    if amount > invoice.balance:
        raise ValidationError(f"Amount exceeds the outstanding balance of ₹{invoice.balance}.")
    payment = Payment.objects.create(firm=invoice.firm, invoice=invoice, amount=amount, paid_on=paid_on or timezone.localdate(), method=method, reference=reference)
    if invoice.balance - amount <= 0:
        invoice.status = Invoice.Status.PAID
        invoice.save(update_fields=["status"])
    return payment


@transaction.atomic
def cancel_invoice(invoice: Invoice) -> None:
    """Only unpaid invoices. The number is never reused; linked time is released for re-billing."""
    if invoice.payments.exists():
        raise ValidationError("Invoices with payments cannot be cancelled.")
    invoice.status = Invoice.Status.CANCELLED
    invoice.save(update_fields=["status"])
    invoice.time_entries.update(invoice=None)
