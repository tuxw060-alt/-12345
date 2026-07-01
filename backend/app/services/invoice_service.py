"""Invoice service — upload handling, AI extraction, and persistence."""

import shutil
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.config import settings
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceUpdate
from app.services.ai_service import ai_service, pdf_to_image
from app.services.client_service import get_client
from app.services.entry_generator import generate_entry_from_invoice
from app.services.entry_service import create_entry as create_entry_record


async def upload_and_extract(
    db: AsyncSession,
    file: UploadFile,
    client_id: str | None = None,
    auto_generate: bool = False,
) -> tuple[Invoice, str | None]:
    """
    Handle invoice upload: save file (image or PDF), convert PDF to image,
    run AI extraction, persist result. Optionally auto-generate journal entry.

    Args:
        db: Database session.
        file: The uploaded file (image or PDF).
        client_id: Optional client ID for context.
        auto_generate: If True, auto-generate journal entry after OCR.

    Returns:
        Tuple of (Invoice record, optional entry_id if auto-generated).
    """
    # Determine client tax type
    tax_type = "small"
    if client_id:
        client = await get_client(db, client_id)
        if client:
            tax_type = client.tax_type

    # Generate unique filename
    invoice_id = str(uuid.uuid4())
    original_filename = file.filename or "invoice.jpg"
    ext = Path(original_filename).suffix.lower() or ".jpg"
    save_name = f"{invoice_id}{ext}"

    # Save original file to uploads directory
    upload_path = settings.upload_path / save_name
    content = await file.read()
    with open(upload_path, "wb") as f:
        f.write(content)

    logger.info(f"Saved uploaded file: {upload_path} ({len(content)} bytes)")

    # If PDF, convert to image for preview and AI processing
    if ext == ".pdf":
        try:
            preview_path = pdf_to_image(upload_path, settings.upload_path)
            logger.info(f"PDF converted to preview image: {preview_path}")
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            # Create invoice with error status
            invoice = Invoice(
                id=invoice_id,
                client_id=client_id,
                image_path=str(upload_path),
                image_filename=original_filename,
                ocr_status="failed",
                ocr_error_msg=f"PDF转换失败: {e}",
            )
            db.add(invoice)
            await db.flush()
            return invoice, None
    else:
        preview_path = upload_path

    # Create invoice record
    invoice = Invoice(
        id=invoice_id,
        client_id=client_id,
        image_path=str(preview_path),
        image_filename=original_filename,
        ocr_status="pending",
    )
    db.add(invoice)
    await db.flush()

    # Run AI extraction on the original file (PDF gets text from layers, images get OCR)
    try:
        result = await ai_service.extract_invoice(upload_path, tax_type)

        if "error" in result:
            invoice.ocr_status = "failed"
            invoice.ocr_error_msg = result["error"]
            logger.error(f"AI extraction failed for {invoice_id}: {result['error']}")
        else:
            # Populate extracted fields
            invoice.invoice_type = result.get("invoice_type")
            invoice.invoice_code = result.get("invoice_code")
            invoice.invoice_number = result.get("invoice_number")

            date_str = result.get("invoice_date")
            if date_str:
                try:
                    invoice.invoice_date = date.fromisoformat(date_str)
                except (ValueError, TypeError):
                    pass

            invoice.total_amount = result.get("total_amount")
            invoice.amount = result.get("amount")
            invoice.tax_amount = result.get("tax_amount")
            invoice.vendor_name = result.get("vendor_name")
            invoice.vendor_tax_id = result.get("vendor_tax_id")
            invoice.buyer_name = result.get("buyer_name")
            invoice.buyer_tax_id = result.get("buyer_tax_id")
            invoice.item_name = result.get("item_name")
            invoice.remarks = result.get("remarks")
            invoice.suggested_subject_code = result.get("suggested_subject_code")
            invoice.suggested_subject_name = result.get("suggested_subject_name")

            # Overall confidence: average of all field confidences
            conf = result.get("confidence", {})
            if conf:
                values = [v for v in conf.values() if isinstance(v, (int, float))]
                invoice.ocr_confidence = sum(values) / len(values) if values else None
                invoice.subject_confidence = conf.get("subject_match")

            invoice.raw_ai_response = result
            invoice.ocr_status = "done"

            # Deduplication check
            if invoice.invoice_number:
                dup_stmt = select(Invoice).where(
                    Invoice.invoice_number == invoice.invoice_number,
                    Invoice.ocr_status == "done",
                    Invoice.id != invoice_id,
                )
                dup_result = await db.execute(dup_stmt)
                if dup_result.scalar_one_or_none():
                    warnings_list = list(result.get("warnings", []))
                    warnings_list.append("⚠️ 该发票号码已存在，可能是重复上传")
                    invoice.raw_ai_response = {**result, "warnings": warnings_list}

            logger.info(f"AI extraction completed for {invoice_id}, "
                       f"confidence: {invoice.ocr_confidence:.0f}%")

    except Exception as e:
        invoice.ocr_status = "failed"
        invoice.ocr_error_msg = str(e)
        logger.error(f"Unexpected error during AI extraction: {e}")

    await db.flush()

    # Auto-generate journal entry if requested and OCR succeeded
    entry_id = None
    if auto_generate and invoice.ocr_status == "done" and client_id:
        try:
            client = await get_client(db, client_id)
            if client:
                entry_data = generate_entry_from_invoice(
                    invoice=invoice,
                    client=client,
                    voucher_date=invoice.invoice_date or date.today(),
                )
                entry = await create_entry_record(db, entry_data)
                entry_id = entry.id
                logger.info(f"Auto-generated entry {entry_id} for invoice {invoice_id}")
        except Exception as e:
            logger.error(f"Failed to auto-generate entry for {invoice_id}: {e}")

    return invoice, entry_id


async def list_invoices(
    db: AsyncSession,
    client_id: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    offset: int = 0,
    limit: int = 50,
):
    stmt = select(Invoice)

    if client_id:
        stmt = stmt.where(Invoice.client_id == client_id)
    if status:
        stmt = stmt.where(Invoice.ocr_status == status)
    if date_from:
        stmt = stmt.where(Invoice.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Invoice.created_at <= date_to)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(Invoice.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return items, total


async def get_invoice(db: AsyncSession, invoice_id: str) -> Invoice | None:
    stmt = select(Invoice).where(Invoice.id == invoice_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_invoice(
    db: AsyncSession, invoice: Invoice, data: InvoiceUpdate
) -> Invoice:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(invoice, field, value)
    await db.flush()
    return invoice


async def delete_invoice(db: AsyncSession, invoice: Invoice) -> None:
    """Delete invoice record and its image file."""
    # Remove image file
    image_path = Path(invoice.image_path)
    if image_path.exists():
        image_path.unlink()
    await db.delete(invoice)
    await db.flush()
