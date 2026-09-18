from django.utils import timezone
from django.core.exceptions import ValidationError
from tracker.models import Query, QueryResponse, Notification, User, Staff
from tracker.services.audit_service import log_audit
from tracker.services.permissions import get_user_role_for_engagement, can_issue_query, can_close_query

def notify_engagement_users(engagement, title, message, link, exclude_user=None, roles=None):
    """
    Utility to create notifications for relevant staff or client users.
    """
    recipients = set()
    
    # Staff members
    team_members = engagement.team_members.filter(is_active=True)
    if roles:
        team_members = team_members.filter(role_on_engagement__in=roles)
    
    for tm in team_members:
        if tm.staff.user and tm.staff.user != exclude_user:
            recipients.add(tm.staff.user)

    # Client contacts if applicable
    if 'Client User' in (roles or []):
        for contact in engagement.client.contacts.filter(status='Active'):
            if contact.user and contact.user != exclude_user:
                recipients.add(contact.user)

    notifications = [
        Notification(recipient=user, title=title, message=message, link=link)
        for user in recipients
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)


def transition_query(query, to_status, user, remarks='', new_due_date=None, request=None, exception_obj=None):
    """
    Executes a query state transition according to the business rules and state machine.
    """
    from_status = query.status
    engagement = query.engagement

    # Check if engagement is locked
    if engagement.status == 'Memo Issued' and to_status != 'Reopen':
        raise ValidationError("This engagement is locked because a Final Summary Memo has been issued. Changes require an approved EX-05 exception.")

    role = get_user_role_for_engagement(user, engagement)
    staff = getattr(user, 'staff_profile', None)

    # Validation logic per transition
    if to_status == 'Pending Internal Review':
        if from_status != 'Draft':
            raise ValidationError(f"Cannot submit for review from {from_status}.")
        # Mandatory fields check
        if not (query.title and query.description and query.area and query.due_date):
            raise ValidationError("Title, description, audit area, and due date are mandatory before submission.")

    elif to_status == 'Issued':
        if from_status == 'Draft':
            if role not in ['Partner', 'Manager', 'Senior']:
                raise ValidationError("Article Assistants cannot issue queries directly. Submit for Internal Review.")
        elif from_status == 'Pending Internal Review':
            if role not in ['Partner', 'Manager', 'Senior']:
                raise ValidationError("Only Seniors, Managers, or Partners can approve and issue queries.")
            if query.raised_by_id == (staff.id if staff else None):
                raise ValidationError("Maker-Checker Violation: The creator of a query cannot review and approve its issue.")
        elif from_status == 'Closed':
            # Reopening closed query
            if role != 'Partner' and not exception_obj:
                raise ValidationError("Only an Audit Partner with an approved EX-04 exception can reopen a closed query.")
        elif from_status not in ['Draft', 'Pending Internal Review', 'Closed']:
            raise ValidationError(f"Invalid transition from {from_status} to Issued.")

        # Ensure query number is generated
        if not query.query_no:
            query.generate_next_query_no()
            query.issued_on = timezone.now()
        
        # If engagement is still 'Planned', move it to 'In Progress'
        if engagement.status == 'Planned':
            engagement.status = 'In Progress'
            engagement.save(update_fields=['status', 'updated_at'])
            log_audit(request, 'Engagement', engagement.engagement_code, 'Status Change', 'status', 'Planned', 'In Progress', user)

    elif to_status == 'Draft' and from_status == 'Pending Internal Review':
        # Rejection back to draft
        if role not in ['Partner', 'Manager', 'Senior']:
            raise ValidationError("Only Seniors, Managers, or Partners can review and return drafts.")
        if not remarks:
            raise ValidationError("Rejection remarks are mandatory when returning a query to Draft.")

    elif to_status == 'Responded':
        if from_status not in ['Issued', 'Info Awaited', 'Pending Client Review']:
            raise ValidationError(f"Cannot record client response from status {from_status}.")

    elif to_status == 'Closed':
        if from_status not in ['Responded', 'Issued', 'Info Awaited']:
            raise ValidationError(f"Cannot close query from status {from_status}.")
        if role not in ['Partner', 'Manager']:
            raise ValidationError("Only Audit Managers and Partners can close queries.")
        if not remarks:
            raise ValidationError("Closure remarks are mandatory when closing a query.")
        query.closed_by = staff
        query.closed_on = timezone.now()
        query.closure_remarks = remarks

    elif to_status == 'Info Awaited':
        if from_status not in ['Responded', 'Issued']:
            raise ValidationError(f"Cannot mark Info Awaited from status {from_status}.")
        if role not in ['Partner', 'Manager']:
            raise ValidationError("Only Audit Managers and Partners can re-issue queries for further info.")
        if not new_due_date:
            raise ValidationError("A new revised due date is mandatory when requesting additional information.")
        query.due_date = new_due_date

    elif to_status == 'Closed - Exception Approved':
        if role != 'Partner':
            raise ValidationError("Only an Audit Partner can close a query via exception approval.")
        if not remarks:
            raise ValidationError("Partner remarks and exception justification are required.")
        query.closed_by = staff
        query.closed_on = timezone.now()
        query.closure_remarks = f"Closed by Exception ({remarks})"

    elif to_status == 'Withdrawn':
        if role != 'Partner' and not exception_obj:
            raise ValidationError("Only an Audit Partner can withdraw an issued query.")
        if not remarks:
            raise ValidationError("Mandatory justification is required to withdraw a query.")
        query.closed_by = staff
        query.closed_on = timezone.now()
        query.closure_remarks = f"Withdrawn: {remarks}"

    # Apply status change
    query.status = to_status
    query.save()

    # Log in append-only AuditTrail
    log_audit(
        request=request,
        entity_type='Query',
        entity_id=query.query_no or f"Draft-{query.id}",
        action='Status Change',
        field_changed='status',
        old_value=from_status,
        new_value=to_status,
        user=user
    )

    # Trigger notifications
    query_display = query.query_no or query.title
    query_link = f"/queries/{query.id}/"

    if to_status == 'Issued':
        notify_engagement_users(
            engagement,
            title=f"New Audit Query Issued: {query_display}",
            message=f"Query '{query.title}' has been issued to the client with due date {query.due_date.strftime('%d-%b-%Y')}.",
            link=query_link,
            exclude_user=user,
            roles=['Client User']
        )
    elif to_status == 'Responded':
        notify_engagement_users(
            engagement,
            title=f"Client Responded: {query_display}",
            message=f"Client has submitted a response to query '{query.title}'.",
            link=query_link,
            exclude_user=user,
            roles=['Partner', 'Manager', 'Senior']
        )
    elif to_status == 'Closed' or to_status == 'Closed - Exception Approved':
        notify_engagement_users(
            engagement,
            title=f"Query Closed: {query_display}",
            message=f"Query '{query.title}' has been marked as {to_status}.",
            link=query_link,
            exclude_user=user,
            roles=['Partner', 'Manager', 'Senior', 'Article Assistant', 'Client User']
        )
    elif to_status == 'Pending Internal Review':
        notify_engagement_users(
            engagement,
            title=f"Draft Query Submitted for Review",
            message=f"Query '{query.title}' submitted by {user.full_name} for internal review.",
            link=query_link,
            exclude_user=user,
            roles=['Partner', 'Manager', 'Senior']
        )

    return query
