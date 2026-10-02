"""/api/purchase — Purchase voucher template + upload."""
from fastapi import APIRouter

from app.accounting.models import VoucherKind
from app.api.voucher_router import add_voucher_routes

router = APIRouter(prefix="/purchase", tags=["purchase"])
add_voucher_routes(router, VoucherKind.PURCHASE)
