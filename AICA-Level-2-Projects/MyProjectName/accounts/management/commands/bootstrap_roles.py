from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from accounts.roles import ADMIN_CFO, APPROVER, AUDITOR_READONLY, DATA_ENTRY, VERIFIER

# Maps each role to (app_label, model_name, [action prefixes]) it needs.
# Actions are Django's default add/change/delete/view permission prefixes.
ROLE_MODEL_PERMS = {
    DATA_ENTRY: [
        ("assets", "asset", ["add", "change", "view"]),
        ("assets", "cwip", ["add", "change", "view"]),
        ("assets", "capexrequisition", ["add", "change", "view"]),
        ("assets", "vendor", ["add", "change", "view"]),
        ("assets", "assetclass", ["view"]),
        ("assets", "document", ["add", "change", "view"]),
        ("assets", "approvalrequest", ["add", "view"]),
        ("transfers", "transferrequest", ["add", "change", "view"]),
        ("disposal", "disposalrequest", ["add", "change", "view"]),
        ("assets", "revaluationrecord", ["add", "change", "view"]),
        ("locations", "location", ["view"]),
        ("locations", "entity", ["view"]),
    ],
    VERIFIER: [
        ("verification", "scanevent", ["add", "change", "view"]),
        ("verification", "physicalverificationrecord", ["add", "change", "view"]),
        ("verification", "verificationcycle", ["add", "change", "view"]),
        ("verification", "maintenancelog", ["add", "view"]),
        ("assets", "asset", ["view"]),
        ("locations", "location", ["view"]),
        ("transfers", "transferrequest", ["add", "view"]),
    ],
    APPROVER: [
        ("assets", "approvalrequest", ["change", "view"]),
        ("assets", "asset", ["view"]),
        ("assets", "cwip", ["view"]),
        ("assets", "capexrequisition", ["change", "view"]),
        ("disposal", "disposalrequest", ["change", "view"]),
        ("transfers", "transferrequest", ["change", "view"]),
        ("assets", "revaluationrecord", ["change", "view"]),
        ("assets", "impairmentcheck", ["add", "change", "view"]),
        ("verification", "verificationcycle", ["view"]),
    ],
    AUDITOR_READONLY: [
        ("assets", "asset", ["view"]),
        ("assets", "cwip", ["view"]),
        ("assets", "capexrequisition", ["view"]),
        ("assets", "vendor", ["view"]),
        ("assets", "document", ["view"]),
        ("assets", "approvalrequest", ["view"]),
        ("assets", "revaluationrecord", ["view"]),
        ("assets", "impairmentcheck", ["view"]),
        ("assets", "depreciationrun", ["view"]),
        ("assets", "bookdepreciationentry", ["view"]),
        ("assets", "taxdepreciationentry", ["view"]),
        ("verification", "scanevent", ["view"]),
        ("verification", "physicalverificationrecord", ["view"]),
        ("verification", "verificationcycle", ["view"]),
        ("transfers", "transferrequest", ["view"]),
        ("disposal", "disposalrequest", ["view"]),
        ("locations", "location", ["view"]),
        ("locations", "entity", ["view"]),
        ("compliance", "financialyear", ["view"]),
        ("compliance", "benamideclaration", ["view"]),
    ],
}


class Command(BaseCommand):
    help = "Create/update the FAR RBAC groups (Data Entry, Verifier, Approver, Admin/CFO, Auditor) with model permissions."

    def handle(self, *args, **options):
        # Data Entry, Verifier, Approver, Auditor get an explicit, narrow permission list.
        for role_name, model_perms in ROLE_MODEL_PERMS.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            perms = []
            for app_label, model_name, actions in model_perms:
                try:
                    ct = ContentType.objects.get(app_label=app_label, model=model_name)
                except ContentType.DoesNotExist:
                    self.stderr.write(f"  ! content type {app_label}.{model_name} not found, skipping")
                    continue
                for action in actions:
                    codename = f"{action}_{model_name}"
                    try:
                        perms.append(Permission.objects.get(content_type=ct, codename=codename))
                    except Permission.DoesNotExist:
                        self.stderr.write(f"  ! permission {codename} on {app_label}.{model_name} not found")
            group.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(f"{role_name}: {len(perms)} permissions"))

        # Admin/CFO gets every permission across the FAR apps (but is still not a Django superuser).
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_CFO)
        far_apps = ["accounts", "locations", "assets", "verification", "transfers", "disposal", "compliance"]
        all_perms = Permission.objects.filter(content_type__app_label__in=far_apps)
        admin_group.permissions.set(all_perms)
        self.stdout.write(self.style.SUCCESS(f"{ADMIN_CFO}: {all_perms.count()} permissions"))

        self.stdout.write(self.style.SUCCESS("RBAC roles bootstrapped."))
