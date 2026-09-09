import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.roles import ADMIN_CFO, APPROVER, AUDITOR_READONLY, DATA_ENTRY, VERIFIER
from assets.models import Asset, AssetClass, CWIP, Vendor
from compliance.models import FinancialYear
from locations.models import Entity, Location

User = get_user_model()


class Command(BaseCommand):
    help = "Seed a working demo: entity, location tree, demo users in every role, vendors, a financial year, and a few sample assets."

    def handle(self, *args, **options):
        entity, _ = Entity.objects.get_or_create(
            name="Demo Listed Company Ltd.",
            defaults={"cin": "L99999MH2000PLC123456", "is_listed_parent": True, "registered_office": "Mumbai, Maharashtra"},
        )

        fy, _ = FinancialYear.objects.get_or_create(
            entity=entity, label="FY 2026-27",
            defaults={"start_date": datetime.date(2026, 4, 1), "end_date": datetime.date(2027, 3, 31)},
        )

        # --- Location tree: Site -> Building -> Floor -> Room -----------
        site, _ = Location.objects.get_or_create(
            entity=entity, parent=None, node_type=Location.NodeType.SITE,
            code="HO", defaults={"name": "Head Office — Mumbai"},
        )
        bld, _ = Location.objects.get_or_create(
            entity=entity, parent=site, node_type=Location.NodeType.BUILDING,
            code="B1", defaults={"name": "Building 1"},
        )
        floor, _ = Location.objects.get_or_create(
            entity=entity, parent=bld, node_type=Location.NodeType.FLOOR,
            code="F2", defaults={"name": "Floor 2"},
        )
        room, _ = Location.objects.get_or_create(
            entity=entity, parent=floor, node_type=Location.NodeType.ROOM,
            code="R01", defaults={"name": "Room 01 — IT"},
        )

        plant_site, _ = Location.objects.get_or_create(
            entity=entity, parent=None, node_type=Location.NodeType.SITE,
            code="PLT", defaults={"name": "Manufacturing Plant — Pune"},
        )
        plant_bld, _ = Location.objects.get_or_create(
            entity=entity, parent=plant_site, node_type=Location.NodeType.BUILDING,
            code="PB1", defaults={"name": "Factory Building 1"},
        )

        # --- Users in every RBAC role ------------------------------------
        users = {}
        specs = [
            ("data_entry1", DATA_ENTRY, "Priya", "Sharma", "Finance"),
            ("verifier1", VERIFIER, "Arjun", "Mehta", "Internal Audit"),
            ("approver1", APPROVER, "Kavita", "Rao", "Finance"),
            ("cfo1", ADMIN_CFO, "Rohan", "Iyer", "Office of the CFO"),
            ("auditor1", AUDITOR_READONLY, "Statutory", "Auditor", "External"),
        ]
        for username, role, first, last, dept in specs:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first, "last_name": last, "department": dept, "is_staff": role == ADMIN_CFO},
            )
            if created:
                user.set_password("FarDemo@2026")
                user.save()
            from django.contrib.auth.models import Group
            group, _ = Group.objects.get_or_create(name=role)
            user.groups.add(group)
            users[username] = user

        # --- Vendors --------------------------------------------------------
        dell, _ = Vendor.objects.get_or_create(name="Dell India Pvt Ltd", defaults={"gstin": "27AAAAA0000A1Z5"})
        related, _ = Vendor.objects.get_or_create(name="Promoter Family Trust Enterprises", defaults={"is_related_party": True})

        # --- A couple of sample assets, already capitalised -----------------
        laptop_class = AssetClass.objects.filter(name="Computers & data processing units").first()
        furniture_class = AssetClass.objects.filter(name="Furniture & fittings").first()

        if laptop_class and not Asset.objects.filter(description="Dell Latitude 5440 laptop").exists():
            Asset.objects.create(
                entity=entity, description="Dell Latitude 5440 laptop", make_model="Latitude 5440",
                asset_class=laptop_class, serial_number="DL5440-0001",
                acquisition_date=datetime.date(2026, 4, 2), put_to_use_date=datetime.date(2026, 4, 5),
                vendor=dell, po_reference="PO-2026-0091", grn_reference="GRN-2026-0210", invoice_reference="INV-DL-8821",
                capitalised_cost=Decimal("85000.00"), depreciation_method=AssetClass.Method.SLM,
                useful_life_years=Decimal("3"), residual_value_pct=Decimal("5"),
                tax_block_code="COMP", tax_wdv_rate_pct=Decimal("40"),
                location=room, department="IT", custodian=users["data_entry1"],
                ownership_status=Asset.OwnershipStatus.OWNED,
                created_by=users["data_entry1"], approved_by=users["approver1"],
                tag_status=Asset.TagStatus.TAGGED, tagged_at=timezone.now(), tagged_by=users["data_entry1"],
                last_verified_date=datetime.date(2026, 6, 1), last_verified_by=users["verifier1"],
            )

        if furniture_class and not Asset.objects.filter(description="Factory workstation desk set").exists():
            Asset.objects.create(
                entity=entity, description="Factory workstation desk set", asset_class=furniture_class,
                acquisition_date=datetime.date(2025, 6, 1), put_to_use_date=datetime.date(2025, 6, 10),
                vendor=related, capitalised_cost=Decimal("240000.00"), depreciation_method=AssetClass.Method.WDV,
                useful_life_years=Decimal("10"), residual_value_pct=Decimal("5"),
                tax_block_code="FURN", tax_wdv_rate_pct=Decimal("10"),
                location=plant_bld, department="Manufacturing",
                ownership_status=Asset.OwnershipStatus.OWNED,
                created_by=users["data_entry1"], approved_by=users["approver1"],
                tag_status=Asset.TagStatus.TAGGED, tagged_at=timezone.now(), tagged_by=users["data_entry1"],
            )

        # --- An open CWIP item awaiting capitalisation -----------------------
        if not CWIP.objects.filter(reference="CWIP-2026-001").exists():
            CWIP.objects.create(
                entity=entity, reference="CWIP-2026-001", description="New CNC machine — plant expansion",
                vendor=dell, po_number="PO-2026-0500", grn_number="GRN-2026-0640", invoice_number="INV-CNC-771",
                invoice_date=datetime.date(2026, 7, 1), base_cost=Decimal("1800000"), freight_cost=Decimal("45000"),
                duty_cost=Decimal("120000"), installation_cost=Decimal("75000"),
                status=CWIP.Status.READY, created_by=users["data_entry1"],
            )

        self.stdout.write(self.style.SUCCESS(
            "Demo data seeded. Log in as data_entry1 / verifier1 / approver1 / cfo1 / auditor1 "
            "with password FarDemo@2026 (change immediately in any real deployment)."
        ))
