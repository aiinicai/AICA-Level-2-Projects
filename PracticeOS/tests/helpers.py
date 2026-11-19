from decimal import Decimal
from types import SimpleNamespace

from accounts.models import Firm, User
from crm.models import Client

PW = "Str0ng-Passw0rd!"


def make_world(sub: str) -> SimpleNamespace:
    """A firm with an admin, a team member, one client and that client's portal login."""
    firm = Firm.objects.create(name=f"{sub.title()} & Co", type="PARTNERSHIP", size="SMALL", subdomain=sub)
    admin = User.objects.create_user(firm, f"admin@{sub}.test", "Admin One", PW, role="ADMIN")
    member = User.objects.create_user(firm, f"member@{sub}.test", "Member One", PW, hourly_rate=Decimal("1000"))
    client = Client.objects.create(firm=firm, name=f"{sub} client", pan=None)
    portal = User.objects.create_user(firm, f"client@{sub}.test", "Portal User", PW, role="CLIENT", client=client)
    return SimpleNamespace(firm=firm, admin=admin, member=member, client=client, portal=portal)
