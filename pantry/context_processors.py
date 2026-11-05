import socket
from .models import PantryItem, MealQueueItem, ShoppingItem, HouseholdProfile

def get_local_network_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "192.168.31.85"

def pantry_stats(request):
    try:
        urgent_count = PantryItem.objects.filter(shelf_life_tier='URGENT').count()
        total_pantry = PantryItem.objects.count()
        queue_count = MealQueueItem.objects.filter(is_cooked=False).count()
        shopping_count = ShoppingItem.objects.filter(is_bought=False).count()
        profile = HouseholdProfile.get_solo()
    except Exception:
        urgent_count = 0
        total_pantry = 0
        queue_count = 0
        shopping_count = 0
        profile = None
    
    local_ip = get_local_network_ip()
    return {
        'urgent_pantry_count': urgent_count,
        'total_pantry_count': total_pantry,
        'meal_queue_count': queue_count,
        'shopping_pending_count': shopping_count,
        'kitchen_profile': profile,
        'local_network_ip': local_ip,
        'mobile_share_url': f"http://{local_ip}:8000/",
    }
