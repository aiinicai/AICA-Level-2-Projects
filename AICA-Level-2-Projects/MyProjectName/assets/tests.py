"""
Focused regression tests for the parts of the blueprint that are easy to
get subtly wrong: the depreciation engine's proration/residual-cap logic,
and the maker-checker rule that an approver can't be the requester.
"""

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from assets.models import Asset, AssetClass, Vendor
from assets.services import approvals as approval_service
from assets.services import depreciation as depreciation_service
from locations.models import Entity, Location

User = get_user_model()


class DepreciationEngineTests(TestCase):
    def setUp(self):
        self.entity = Entity.objects.create(name="Test Co")
        self.site = Location.objects.create(entity=self.entity, node_type="SITE", name="HO", code="HO")
        self.vendor = Vendor.objects.create(name="Test Vendor")
        self.user = User.objects.create_user("runner", password="x")
        self.asset_class = AssetClass.objects.create(
            name="Test class", useful_life_years=Decimal("5"), default_method=AssetClass.Method.SLM,
        )

    def _make_asset(self, method, cost, put_to_use, life=Decimal("5")):
        return Asset.objects.create(
            entity=self.entity, description="Test asset", asset_class=self.asset_class,
            acquisition_date=put_to_use, put_to_use_date=put_to_use, vendor=self.vendor,
            capitalised_cost=cost, depreciation_method=method, useful_life_years=life,
            residual_value_pct=Decimal("5"), location=self.site, created_by=self.user,
        )

    def test_slm_full_year_matches_straight_line_formula(self):
        asset = self._make_asset(AssetClass.Method.SLM, Decimal("100000"), datetime.date(2025, 4, 1))
        run = depreciation_service.run_schedule_ii(
            self.entity, datetime.date(2025, 4, 1), datetime.date(2026, 3, 31), self.user,
        )
        entry = run.book_entries.get(asset=asset)
        # depreciable amount = 100000 - 5% residual = 95000; /5 years = 19000/yr
        self.assertAlmostEqual(float(entry.depreciation_amount), 19000.0, delta=50)

    def test_depreciation_never_exceeds_residual_floor(self):
        """Running many years of SLM depreciation must never push closing WDV below the 5% residual value."""
        asset = self._make_asset(AssetClass.Method.SLM, Decimal("100000"), datetime.date(2020, 4, 1))
        closing = None
        for year in range(2020, 2030):
            run = depreciation_service.run_schedule_ii(
                self.entity, datetime.date(year, 4, 1), datetime.date(year + 1, 3, 31), self.user,
            )
            entry = run.book_entries.get(asset=asset)
            closing = entry.closing_wdv
        residual = asset.residual_value()
        self.assertGreaterEqual(closing, residual)

    def test_mid_year_addition_is_prorated(self):
        """An asset put to use mid-year should depreciate for a fraction of the annual charge, not the full year."""
        asset = self._make_asset(AssetClass.Method.SLM, Decimal("100000"), datetime.date(2025, 10, 1))
        run = depreciation_service.run_schedule_ii(
            self.entity, datetime.date(2025, 4, 1), datetime.date(2026, 3, 31), self.user,
        )
        entry = run.book_entries.get(asset=asset)
        annual_full = Decimal("95000") / Decimal("5")  # 19000
        self.assertLess(entry.depreciation_amount, annual_full)
        self.assertGreater(entry.depreciation_amount, 0)


class MakerCheckerTests(TestCase):
    def setUp(self):
        self.entity = Entity.objects.create(name="Test Co")
        self.site = Location.objects.create(entity=self.entity, node_type="SITE", name="HO", code="HO")
        self.vendor = Vendor.objects.create(name="Test Vendor")
        self.asset_class = AssetClass.objects.create(name="Test class", useful_life_years=Decimal("5"))
        self.maker = User.objects.create_user("maker", password="x")
        self.checker = User.objects.create_user("checker", password="x")
        self.asset = Asset.objects.create(
            entity=self.entity, description="Test asset", asset_class=self.asset_class,
            acquisition_date=datetime.date(2025, 4, 1), put_to_use_date=datetime.date(2025, 4, 1),
            vendor=self.vendor, capitalised_cost=Decimal("50000"), depreciation_method="SLM",
            useful_life_years=Decimal("5"), location=self.site, created_by=self.maker,
        )

    def test_requester_cannot_approve_own_request(self):
        from assets.models import ApprovalRequest
        req = approval_service.create_request(self.maker, self.asset, ApprovalRequest.Action.ASSET_CREATE, "test")
        with self.assertRaises(approval_service.DifferentUserRequiredError):
            approval_service.decide(req, self.maker, approve=True)

    def test_different_user_can_approve(self):
        from assets.models import ApprovalRequest
        req = approval_service.create_request(self.maker, self.asset, ApprovalRequest.Action.ASSET_CREATE, "test")
        approval_service.decide(req, self.checker, approve=True)
        req.refresh_from_db()
        self.assertEqual(req.status, ApprovalRequest.Status.APPROVED)
