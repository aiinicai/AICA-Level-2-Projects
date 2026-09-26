"""/api/sales — Sales voucher template + upload."""
from fastapi import APIRouter

from app.accounting.models import VoucherKind
from app.api.voucher_router import add_voucher_routes

router = APIRouter(prefix="/sales", tags=["sales"])
add_voucher_routes(router, VoucherKind.SALES)
