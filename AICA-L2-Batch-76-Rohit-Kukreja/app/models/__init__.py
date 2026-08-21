"""Domain models. Build Prompt v2 §5.

Importing this package registers every table on `Base.metadata`, which is
what Alembic autogenerate walks.
"""

from app.models.engagement import (
    BoardMeeting,
    DirectorChange,
    Engagement,
    EngagementResponse,
    FieldCatalog,
    IfcDeficiency,
    Litigation,
    StatutoryDue,
)
from app.models.enums import (
    CommentStatus,
    CompanyType,
    Designation,
    DocumentStatus,
    EngagementStatus,
    Framework,
    GoingConcern,
    KmpRole,
    OpinionType,
    ResponseSource,
    Role,
)
from app.models.issuance import AuditLog, DocumentInstance, UdinRegister
from app.models.masters import (
    Banker,
    Client,
    ClientProfile,
    Director,
    Firm,
    Kmp,
    Partner,
    User,
)
from app.models.workflow import ReviewComment

__all__ = [
    "AuditLog",
    "Banker",
    "BoardMeeting",
    "Client",
    "ClientProfile",
    "CommentStatus",
    "CompanyType",
    "Designation",
    "Director",
    "DirectorChange",
    "DocumentInstance",
    "DocumentStatus",
    "Engagement",
    "EngagementResponse",
    "EngagementStatus",
    "FieldCatalog",
    "Firm",
    "Framework",
    "GoingConcern",
    "IfcDeficiency",
    "Kmp",
    "KmpRole",
    "Litigation",
    "OpinionType",
    "Partner",
    "ResponseSource",
    "ReviewComment",
    "Role",
    "StatutoryDue",
    "UdinRegister",
    "User",
]
