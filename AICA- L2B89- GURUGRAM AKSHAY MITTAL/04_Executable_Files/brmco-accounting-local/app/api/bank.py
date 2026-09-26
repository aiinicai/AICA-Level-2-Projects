"""/api/bank/receipt and /api/bank/payment — Bank entry templates + upload."""
from fastapi import APIRouter

from app.accounting.models import VoucherKind
from app.api.voucher_router import add_voucher_routes

router = APIRouter(prefix="/bank", tags=["bank"])
add_voucher_routes(router, VoucherKind.RECEIPT, "/receipt")
add_voucher_routes(router, VoucherKind.PAYMENT, "/payment")
