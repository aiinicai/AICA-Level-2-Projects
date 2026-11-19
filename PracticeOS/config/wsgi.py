import os

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()

try:
    call_command("migrate", interactive=False)
    from accounts.models import Firm

    if not Firm.objects.filter(subdomain="demo").exists():
        call_command("seed_demo")
except Exception as e:
    print(f"Startup check warning: {e}")
