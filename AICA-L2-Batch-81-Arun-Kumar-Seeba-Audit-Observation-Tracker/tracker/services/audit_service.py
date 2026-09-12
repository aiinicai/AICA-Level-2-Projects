from django.utils import timezone
from tracker.models import AuditTrail

def get_client_ip(request):
    if not request:
        return ''
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip

def log_audit(request=None, entity_type='', entity_id='', action='', field_changed='', old_value='', new_value='', user=None, performed_by_name=''):
    if user is None and request and request.user and request.user.is_authenticated:
        user = request.user
    
    if not performed_by_name:
        if user:
            performed_by_name = f"{user.full_name} ({user.email})"
        else:
            performed_by_name = "System / Automated"

    ip_address = get_client_ip(request)

    AuditTrail.objects.create(
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        field_changed=field_changed[:100],
        old_value=str(old_value) if old_value is not None else '',
        new_value=str(new_value) if new_value is not None else '',
        performed_by=user if (user and user.is_authenticated) else None,
        performed_by_name=performed_by_name[:150],
        performed_on=timezone.now(),
        ip_address=ip_address
    )
