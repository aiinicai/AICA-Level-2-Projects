"""Shared endpoints for every voucher category (template download + upload/validate)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from app.accounting.models import VoucherKind
from app.container import Container, get_container

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def add_voucher_routes(router: APIRouter, kind: VoucherKind, prefix: str = "") -> None:
    @router.get(f"{prefix}/template", summary=f"Download the {kind.label} Excel template")
    def download_template(c: Container = Depends(get_container)) -> Response:
        name, content = c.imports.template(kind)
        return Response(content, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @router.get(f"{prefix}/sample", summary=f"Download a filled {kind.label} sample (matches demo masters)")
    def download_sample(c: Container = Depends(get_container)) -> Response:
        name, content = c.imports.template(kind, sample=True)
        return Response(content, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @router.post(f"{prefix}/upload", summary=f"Upload and validate a {kind.label} Excel file")
    async def upload(file: UploadFile = File(...), c: Container = Depends(get_container)) -> dict:
        content = await file.read()
        return c.imports.upload(kind, file.filename or "upload.xlsx", content)
