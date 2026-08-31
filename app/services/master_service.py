from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.branch import Branch
from app.models.payment_channel import PaymentChannel, ChannelMapping
from app.models.aggregator import Aggregator
from app.models.accounting_head import AccountingHead
from app.models.setting import ApplicationSetting
from app.services.audit_service import log_action

# --- BRANCH MASTER ---
def get_branches(db: Session, active_only: bool = False) -> List[Branch]:
    query = db.query(Branch)
    if active_only:
        query = query.filter(Branch.is_active == True)
    return query.order_by(Branch.name).all()

def get_branch_by_id(db: Session, branch_id: int) -> Optional[Branch]:
    return db.query(Branch).filter(Branch.id == branch_id).first()

def get_branch_by_code(db: Session, code: str) -> Optional[Branch]:
    return db.query(Branch).filter(Branch.code == code).first()

def create_branch(db: Session, data: dict, current_user=None) -> Branch:
    branch = Branch(**data)
    db.add(branch)
    db.commit()
    db.refresh(branch)
    log_action(db, "CREATE", "Branch", branch.id, None, data, user=current_user)
    return branch

def update_branch(db: Session, branch_id: int, data: dict, current_user=None) -> Optional[Branch]:
    branch = get_branch_by_id(db, branch_id)
    if not branch:
        return None
    old_data = {"name": branch.name, "code": branch.code, "opening_cash_balance": branch.opening_cash_balance, "is_active": branch.is_active}
    for key, value in data.items():
        setattr(branch, key, value)
    db.commit()
    db.refresh(branch)
    log_action(db, "UPDATE", "Branch", branch.id, old_data, data, user=current_user)
    return branch

# --- PAYMENT CHANNEL MASTER ---
def get_channels(db: Session, active_only: bool = False) -> List[PaymentChannel]:
    query = db.query(PaymentChannel)
    if active_only:
        query = query.filter(PaymentChannel.is_active == True)
    return query.order_by(PaymentChannel.id).all()

def create_channel(db: Session, data: dict, current_user=None) -> PaymentChannel:
    channel = PaymentChannel(**data)
    db.add(channel)
    db.commit()
    db.refresh(channel)
    log_action(db, "CREATE", "PaymentChannel", channel.id, None, data, user=current_user)
    return channel

def create_channel_mapping(db: Session, channel_id: int, alias: str, branch_id: Optional[int] = None) -> ChannelMapping:
    mapping = ChannelMapping(payment_channel_id=channel_id, alias=alias.strip().lower(), branch_id=branch_id)
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping

# --- AGGREGATOR MASTER ---
def get_aggregators(db: Session, active_only: bool = False) -> List[Aggregator]:
    query = db.query(Aggregator)
    if active_only:
        query = query.filter(Aggregator.is_active == True)
    return query.order_by(Aggregator.name).all()

def create_aggregator(db: Session, data: dict, current_user=None) -> Aggregator:
    agg = Aggregator(**data)
    db.add(agg)
    db.commit()
    db.refresh(agg)
    log_action(db, "CREATE", "Aggregator", agg.id, None, data, user=current_user)
    return agg

# --- ACCOUNTING HEAD MASTER ---
def get_accounting_heads(db: Session, active_only: bool = False) -> List[AccountingHead]:
    query = db.query(AccountingHead)
    if active_only:
        query = query.filter(AccountingHead.is_active == True)
    return query.order_by(AccountingHead.name).all()

def create_accounting_head(db: Session, data: dict, current_user=None) -> AccountingHead:
    head = AccountingHead(**data)
    db.add(head)
    db.commit()
    db.refresh(head)
    log_action(db, "CREATE", "AccountingHead", head.id, None, data, user=current_user)
    return head

# --- APPLICATION SETTINGS ---
def get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(ApplicationSetting).filter(ApplicationSetting.key == key).first()
    return setting.value if setting else default

def set_setting(db: Session, key: str, value: str, description: Optional[str] = None, current_user=None):
    setting = db.query(ApplicationSetting).filter(ApplicationSetting.key == key).first()
    old_val = setting.value if setting else None
    if setting:
        setting.value = value
        if description:
            setting.description = description
    else:
        setting = ApplicationSetting(key=key, value=value, description=description)
        db.add(setting)
    db.commit()
    log_action(db, "UPDATE_SETTING", "ApplicationSetting", key, old_val, value, user=current_user)
    return setting
