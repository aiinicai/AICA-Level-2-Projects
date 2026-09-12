from tracker.models import EngagementTeam, Staff, ClientContact

def get_user_role_for_engagement(user, engagement):
    """
    Returns the role of the user on the specific engagement:
    'Admin', 'Partner', 'Manager', 'Senior', 'Article Assistant', 'Client User', 'Client Coordinator', or None.
    """
    if not user or not user.is_authenticated:
        return None

    if user.user_type == 'ADMIN' or user.is_superuser:
        return 'Admin'

    if user.user_type == 'CLIENT':
        # Check if user is associated with this engagement's client
        contact = getattr(user, 'client_contact', None)
        if contact and contact.client_id == engagement.client_id:
            if contact.is_primary_coordinator:
                return 'Client Coordinator'
            return 'Client User'
        return None

    if user.user_type == 'STAFF':
        staff = getattr(user, 'staff_profile', None)
        if not staff:
            return None
        
        assignment = EngagementTeam.objects.filter(
            engagement=engagement,
            staff=staff,
            is_active=True
        ).first()

        if assignment:
            return assignment.role_on_engagement
        return None

    return None


def can_manage_masters(user):
    return user.is_authenticated and (user.user_type == 'ADMIN' or user.is_superuser)


def can_create_engagement(user):
    if not user.is_authenticated:
        return False
    if user.user_type == 'ADMIN' or user.is_superuser:
        return True
    if user.user_type == 'STAFF':
        staff = getattr(user, 'staff_profile', None)
        if staff and staff.designation in ['Partner', 'Manager']:
            return True
    return False


def can_assign_team(user, engagement):
    if not user.is_authenticated:
        return False
    if user.user_type == 'ADMIN' or user.is_superuser:
        return True
    if user.user_type == 'STAFF':
        staff = getattr(user, 'staff_profile', None)
        if staff and staff.designation in ['Partner', 'Manager']:
            return True
    role = get_user_role_for_engagement(user, engagement)
    return role in ['Partner', 'Manager']


def can_create_query(user, engagement):
    if not user.is_authenticated or user.user_type != 'STAFF':
        return False
    role = get_user_role_for_engagement(user, engagement)
    return role in ['Partner', 'Manager', 'Senior', 'Article Assistant']


def can_issue_query(user, query):
    """
    Checks if user can issue query directly to client or approve draft.
    Requires Senior, Manager, or Partner role on engagement.
    Enforces maker-checker: Creator cannot approve issue if pending review.
    """
    if not user.is_authenticated or user.user_type != 'STAFF':
        return False
    
    role = get_user_role_for_engagement(user, query.engagement)
    if role not in ['Partner', 'Manager', 'Senior']:
        return False

    staff = getattr(user, 'staff_profile', None)
    
    # If query is in Pending Internal Review, maker != checker rule:
    if query.status == 'Pending Internal Review':
        if query.raised_by_id == staff.id:
            return False # Creator cannot review/issue their own draft
        return True

    # If query is in Draft:
    if query.status == 'Draft':
        # Article Assistants cannot self-issue
        if role == 'Article Assistant':
            return False
        # Seniors, Managers, Partners can self-issue draft if they created it,
        # or issue drafted query if they are different from article
        return True

    return False


def can_edit_query(user, query):
    """
    Drafts can be edited by creator or Seniors/Managers/Partners.
    Issued queries can only be edited by Manager or Partner.
    """
    if not user.is_authenticated or user.user_type != 'STAFF':
        return False
    
    # Locked if engagement has Final Memo Issued
    if query.engagement.status == 'Memo Issued':
        return False

    role = get_user_role_for_engagement(user, query.engagement)
    if not role:
        return False

    if query.status in ['Draft', 'Pending Internal Review']:
        staff = getattr(user, 'staff_profile', None)
        if query.raised_by_id == (staff.id if staff else None):
            return True
        return role in ['Partner', 'Manager', 'Senior']

    # If already issued or beyond
    return role in ['Partner', 'Manager']


def can_close_query(user, query):
    if not user.is_authenticated or user.user_type != 'STAFF':
        return False
    if query.engagement.status == 'Memo Issued':
        return False
    role = get_user_role_for_engagement(user, query.engagement)
    return role in ['Partner', 'Manager']


def can_request_exception(user, engagement):
    if not user.is_authenticated or user.user_type != 'STAFF':
        return False
    role = get_user_role_for_engagement(user, engagement)
    return role in ['Partner', 'Manager', 'Senior']


def can_approve_exception(user, exception_obj):
    if not user.is_authenticated or user.user_type != 'STAFF':
        return False
    role = get_user_role_for_engagement(user, exception_obj.engagement)
    if role != 'Partner':
        return False
    
    # Check if this partner raised the exception and if other partners exist
    staff = getattr(user, 'staff_profile', None)
    if not staff:
        return False
    
    # Partner cannot approve own request if another partner exists on team or firm
    if exception_obj.requested_by_id == staff.id:
        other_partners_count = Staff.objects.filter(designation='Partner', status='Active').exclude(id=staff.id).count()
        if other_partners_count > 0:
            return False # Must route to another partner
    
    return True


def can_generate_memo(user, engagement):
    if not user.is_authenticated or user.user_type != 'STAFF':
        return False
    role = get_user_role_for_engagement(user, engagement)
    return role in ['Partner', 'Manager']


def can_signoff_memo(user, engagement):
    if not user.is_authenticated or user.user_type != 'STAFF':
        return False
    role = get_user_role_for_engagement(user, engagement)
    return role == 'Partner'


def can_view_query(user, query):
    if not user.is_authenticated:
        return False
    if user.user_type == 'ADMIN' or user.is_superuser:
        return True
    
    if user.user_type == 'CLIENT':
        contact = getattr(user, 'client_contact', None)
        if not contact or contact.client_id != query.engagement.client_id:
            return False
        # Client cannot view Draft or Pending Internal Review queries!
        if query.status in ['Draft', 'Pending Internal Review']:
            return False
        return True

    if user.user_type == 'STAFF':
        role = get_user_role_for_engagement(user, query.engagement)
        return role is not None

    return False


def can_post_response(user, query):
    if not user.is_authenticated:
        return False
    if query.is_terminal:
        return False

    if user.user_type == 'CLIENT':
        contact = getattr(user, 'client_contact', None)
        if not contact or contact.client_id != query.engagement.client_id:
            return False
        # Only allowed when issued or responded or info awaited
        return query.status in ['Issued', 'Responded', 'Info Awaited', 'Pending Client Review']

    if user.user_type == 'STAFF':
        role = get_user_role_for_engagement(user, query.engagement)
        return role in ['Partner', 'Manager', 'Senior', 'Article Assistant']

    return False
