"""Sample lease: monthly payments, one reassessment (extension, revised rate), one partial termination."""
import datetime as dt
from decimal import Decimal as D

from .models import Event, LeaseTerms


def sample_terms(ref='SAMPLE-001'):
    return LeaseTerms(ref=ref, lessor='Harbour Properties LLC', asset='Office floor 4 – Harbour Tower', signing_date=dt.date(2024, 12, 10), commencement=dt.date(2025, 1, 1),
                      end_date=dt.date(2027, 12, 31), functional_currency='AED', currency='AED', payment_amount=D('25000'), frequency='monthly', timing='arrears',
                      discount_rate=D('0.065'), rate_basis='IBR', day_count='ACT/365', compounding='annual', depreciation_method='straight_line',
                      useful_life_years=D(0), initial_direct_costs=D('4000'), incentives_received=D('10000'), restoration_obligation=D('8000'),
                      notes='Sample lease for demonstration. Rate, costs and dates are illustrative.')


def sample_events():
    return [
        Event('term_reassessment', dt.date(2026, 1, 1), {'new_end_date': '2028-12-31', 'revised_rate': '7.0'}, 'Extension option now reasonably certain (+12 months)'),
        Event('termination', dt.date(2026, 7, 1), {'scope_pct': '30', 'termination_payment': '15000'}, 'Surrender of 30% of the floor area'),
    ]


def load_sample(store, with_events=True, ref='SAMPLE-001'):
    store.save_lease(sample_terms(ref), 'sample lease')
    if with_events:
        for e in sample_events():
            store.commit_event(ref, e)
    return ref
