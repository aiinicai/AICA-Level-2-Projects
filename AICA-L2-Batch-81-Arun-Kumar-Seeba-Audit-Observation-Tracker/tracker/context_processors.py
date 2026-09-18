from tracker.models import Notification, Staff, ClientContact

def tracker_context(request):
    if not request.user.is_authenticated:
        return {}
    
    user = request.user
    staff = getattr(user, 'staff_profile', None)
    contact = getattr(user, 'client_contact', None)
    
    unread_notifications = Notification.objects.filter(recipient=user, is_read=False).order_by('-created_at')
    unread_count = unread_notifications.count()
    recent_notifications = unread_notifications[:5]

    return {
        'current_user': user,
        'current_staff': staff,
        'current_contact': contact,
        'unread_notifications_count': unread_count,
        'recent_notifications': recent_notifications,
        'is_admin': user.user_type == 'ADMIN' or user.is_superuser,
        'is_partner': staff.designation == 'Partner' if staff else False,
        'is_manager': staff.designation == 'Manager' if staff else False,
        'is_senior': staff.designation == 'Senior' if staff else False,
        'is_article': staff.designation == 'Article Assistant' if staff else False,
        'is_client': user.user_type == 'CLIENT',
    }
