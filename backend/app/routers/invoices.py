"""Invoice API routes — upload, list, review, delete."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.schemas.invoice import (
    InvoiceResponse,
    InvoiceUpdate,
    InvoiceListResponse,
)
from app.services import invoice_service

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


class UploadResponse(BaseModel):
    invoice: InvoiceResponse
    entry_id: str | None = None


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_invoice(
    file: UploadFile = File(..., description="发票文件 (图片或PDF)"),
    client_id: str | None = Query(None, description="所属客户ID"),
    auto_generate: bool = Query(False, description="识别后自动生成记账凭证"),
    db: AsyncSession = Depends(get_db),
):
    """Upload an invoice (image or PDF), AI extract, optionally auto-generate entry."""
    # Validate file type
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".pdf"}
    if file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    else:
        ext = ".jpg"
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，支持: {', '.join(allowed)}",
        )

    invoice, entry_id = await invoice_service.upload_and_extract(
        db, file, client_id, auto_generate=auto_generate
    )
    return UploadResponse(
        invoice=InvoiceResponse.model_validate(invoice),
        entry_id=entry_id,
    )


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    client_id: str | None = Query(None),
    status: str | None = Query(None, description="pending / done / failed"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    items, total = await invoice_service.list_invoices(
        db, client_id, status, date_from, date_to, offset, limit
    )
    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: str, db: AsyncSession = Depends(get_db)):
    invoice = await invoice_service.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    return InvoiceResponse.model_validate(invoice)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str, data: InvoiceUpdate, db: AsyncSession = Depends(get_db)
):
    """Manually correct AI-extracted fields."""
    invoice = await invoice_service.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    invoice = await invoice_service.update_invoice(db, invoice, data)
    return InvoiceResponse.model_validate(invoice)


@router.delete("/{invoice_id}", status_code=204)
async def delete_invoice(invoice_id: str, db: AsyncSession = Depends(get_db)):
    invoice = await invoice_service.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    await invoice_service.delete_invoice(db, invoice)
    return None
