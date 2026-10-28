"""Account mapping: internal account codes -> display names and default Tally ledger names (all user-configurable)."""
from .engine import ACCOUNTS

DEFAULT_LEDGERS = {
    'ROU_COST': 'Right-of-Use Assets',
    'ROU_ACCDEP': 'Accumulated Depreciation - ROU Assets',
    'LEASE_LIAB': 'Lease Liability',
    'INTEREST_EXP': 'Interest on Lease Liability',
    'DEP_EXP': 'Depreciation - ROU Assets',
    'CASH': 'Bank Account',
    'PROVISION': 'Restoration Provision',
    'PREPAID': 'Prepaid Lease Payments',
    'GAIN_LOSS': 'Gain/Loss on Lease Modification',
    'LEASE_EXP': 'Short-term & Low-value Lease Expense',
    'ACCRUED_LEASE': 'Accrued Lease Payable',
}


def default_map():
    return {k: {'label': ACCOUNTS[k], 'ledger': DEFAULT_LEDGERS[k]} for k in ACCOUNTS}


def journal_rows(journal, account_map=None):
    """Flatten a journal for display: (account label, ledger, debit, credit, memo)."""
    m = account_map or default_map()
    return [(m.get(l.account, {}).get('label', l.account), m.get(l.account, {}).get('ledger', l.account), l.debit, l.credit, l.memo) for l in journal.lines]
