from decimal import Decimal

from django.core.management.base import BaseCommand

from assets.models import AssetClass

# Blueprint §04 — Schedule II useful life reference table.
SCHEDULE_II_CLASSES = [
    # name, useful_life_years, method, is_intangible, notes
    ("Buildings — RCC frame", Decimal("60"), AssetClass.Method.SLM, False, "Factory buildings: 30 years"),
    ("Buildings — factory (RCC frame)", Decimal("30"), AssetClass.Method.SLM, False, "Factory buildings variant"),
    ("Plant & machinery (general)", Decimal("15"), AssetClass.Method.WDV, False, "Continuous process plant: 25 years"),
    ("Plant & machinery (continuous process)", Decimal("25"), AssetClass.Method.WDV, False, "Continuous process plant"),
    ("Computers & data processing units", Decimal("3"), AssetClass.Method.SLM, False, "Servers/networks: 6 years"),
    ("Servers and networks", Decimal("6"), AssetClass.Method.SLM, False, "Servers/networks"),
    ("Office equipment", Decimal("5"), AssetClass.Method.WDV, False, ""),
    ("Furniture & fittings", Decimal("10"), AssetClass.Method.WDV, False, ""),
    ("Motor vehicles (cars)", Decimal("8"), AssetClass.Method.WDV, False, ""),
    ("Motor vehicles (commercial)", Decimal("8"), AssetClass.Method.WDV, False, "Commercial vehicles: 6–8 years"),
    ("Intangible assets", None, AssetClass.Method.SLM, True, "Per Ind AS 38 — not governed by Schedule II"),
]


class Command(BaseCommand):
    help = "Seed the AssetClass master with the Schedule II useful-life reference table (blueprint §04)."

    def handle(self, *args, **options):
        created, updated = 0, 0
        for name, life, method, intangible, notes in SCHEDULE_II_CLASSES:
            obj, was_created = AssetClass.objects.update_or_create(
                name=name,
                defaults={
                    "useful_life_years": life,
                    "default_method": method,
                    "is_intangible": intangible,
                    "residual_value_pct": Decimal("0") if intangible else Decimal("5.00"),
                    "notes": notes,
                },
            )
            created += was_created
            updated += not was_created
        self.stdout.write(self.style.SUCCESS(f"Asset classes: {created} created, {updated} updated."))
