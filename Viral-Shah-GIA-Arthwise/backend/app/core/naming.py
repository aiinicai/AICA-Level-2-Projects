import re
from sqlalchemy.orm import Session

def clean_client_name_prefix(name: str) -> str:
    """
    Cleans client name into a concise uppercase alphanumeric prefix (up to 8 chars).
    Strips salutations (Dr, Mr, Mrs, M/s) and corporate suffixes (Pvt Ltd, LLP, etc.).
    """
    if not name:
        return "CLIENT"
    
    # Strip salutations and corporate designations
    cleaned = re.sub(
        r'(?i)\b(m/s|dr|mr|mrs|ms|shri|smt|private\s+limited|pvt\s+ltd|pvt|ltd|limited|llp|corp|corporation|inc|enterprises|enterprise|solutions|services|company|co)\b',
        '',
        name
    ).strip()
    
    # Take first word or main name token
    words = [w for w in cleaned.split() if w and len(re.sub(r'[^A-Za-z0-9]', '', w)) > 1]
    first_token = words[0] if words else (name.split()[0] if name.split() else "CLIENT")
    
    alpha = re.sub(r'[^A-Za-z0-9]', '', first_token).upper()
    if not alpha or len(alpha) < 2:
        alpha = re.sub(r'[^A-Za-z0-9]', '', cleaned).upper()
    if not alpha:
        alpha = "CLIENT"
        
    return alpha[:8]

def generate_client_code(client_name: str, db: Session) -> str:
    """
    Generates client code with client name prefix and a 5-digit suffix.
    Format: CLI-{CLIENT_NAME}-{00001}
    """
    from backend.app.models.models import Client
    prefix = clean_client_name_prefix(client_name)
    pattern = f"CLI-{prefix}-%"
    count = db.query(Client).filter(Client.client_code.like(pattern)).count()
    suffix_num = count + 1
    code = f"CLI-{prefix}-{suffix_num:05d}"
    while db.query(Client).filter(Client.client_code == code).first():
        suffix_num += 1
        code = f"CLI-{prefix}-{suffix_num:05d}"
    return code

def generate_proposal_code(client_name: str, db: Session) -> str:
    """
    Generates proposal / Case ID with client name prefix and a 5-digit suffix.
    Format: PROP-{CLIENT_NAME}-{00001}
    """
    from backend.app.models.models import Proposal
    prefix = clean_client_name_prefix(client_name)
    pattern = f"PROP-{prefix}-%"
    count = db.query(Proposal).filter(Proposal.proposal_code.like(pattern)).count()
    suffix_num = count + 1
    code = f"PROP-{prefix}-{suffix_num:05d}"
    while db.query(Proposal).filter(Proposal.proposal_code == code).first():
        suffix_num += 1
        code = f"PROP-{prefix}-{suffix_num:05d}"
    return code
