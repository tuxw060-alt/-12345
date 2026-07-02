"""JournalEntry API routes — CRUD + auto-generate from invoice."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.journal_entry import (
    EntryCreate,
    EntryUpdate,
    EntryResponse,
    EntryListResponse,
    EntryGenerateRequest,
    EntryGenerateResponse,
)
from app.services import entry_service, invoice_service, client_service
from app.services.entry_generator import generate_entry_from_invoice

router = APIRouter(prefix="/api/v1/entries", tags=["entries"])


@router.get("", response_model=EntryListResponse)
async def list_entries(
    client_id: str | None = Query(None),
    status: str | None = Query(None, description="draft / confirmed / exported"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    items, total = await entry_service.list_entries(
        db, client_id, status, date_from, date_to, offset, limit
    )
    return EntryListResponse(
        items=[EntryResponse.model_validate(item) for item in items],
        total=total,
    )


@router.post("/generate", response_model=EntryCreate)
async def generate_entry(
    data: EntryGenerateRequest, db: AsyncSession = Depends(get_db)
):
    """Auto-generate a journal entry from an AI-processed invoice."""
    invoice = await invoice_service.get_invoice(db, data.invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")

    if invoice.ocr_status != "done":
        raise HTTPException(status_code=400, detail="发票尚未完成AI识别，请等待处理完毕")

    client = await client_service.get_client(db, data.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="客户不存在")

    entry_data = generate_entry_from_invoice(
        invoice=invoice,
        client=client,
        voucher_date=data.voucher_date or invoice.invoice_date or date.today(),
        voucher_type=data.voucher_type,
        summary=data.summary,
    )

    return entry_data


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(entry_id: str, db: AsyncSession = Depends(get_db)):
    entry = await entry_service.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="凭证不存在")
    return EntryResponse.model_validate(entry)


@router.post("", response_model=EntryResponse, status_code=201)
async def create_entry(data: EntryCreate, db: AsyncSession = Depends(get_db)):
    entry = await entry_service.create_entry(db, data)
    # Re-fetch to get loaded relationships
    entry = await entry_service.get_entry(db, entry.id)
    return EntryResponse.model_validate(entry)


@router.put("/{entry_id}", response_model=EntryResponse)
async def update_entry(
    entry_id: str, data: EntryUpdate, db: AsyncSession = Depends(get_db)
):
    entry = await entry_service.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="凭证不存在")
    if entry.status == "exported":
        raise HTTPException(status_code=400, detail="已导出的凭证不可修改")
    entry = await entry_service.update_entry(db, entry, data)
    return EntryResponse.model_validate(entry)


@router.post("/{entry_id}/confirm", response_model=EntryResponse)
async def confirm_entry(entry_id: str, db: AsyncSession = Depends(get_db)):
    """Confirm a draft entry, making it ready for export."""
    entry = await entry_service.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="凭证不存在")
    entry = await entry_service.confirm_entry(db, entry)
    return EntryResponse.model_validate(entry)


@router.post("/batch-confirm")
async def batch_confirm(
    entry_ids: list[str],
    db: AsyncSession = Depends(get_db),
):
    """Batch confirm multiple draft entries at once."""
    confirmed = []
    failed = []
    for eid in entry_ids:
        entry = await entry_service.get_entry(db, eid)
        if not entry:
            failed.append({"id": eid, "reason": "凭证不存在"})
            continue
        if entry.status != "draft":
            failed.append({"id": eid, "reason": "只有草稿状态的凭证可以确认"})
            continue
        try:
            await entry_service.confirm_entry(db, entry)
            confirmed.append(eid)
        except Exception as e:
            failed.append({"id": eid, "reason": str(e)})
    return {"confirmed": len(confirmed), "failed": failed}


@router.post("/batch-delete")
async def batch_delete(
    entry_ids: list[str],
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple entries. Exported entries are kept as audit records."""
    deleted = []
    failed = []
    for eid in entry_ids:
        entry = await entry_service.get_entry(db, eid)
        if not entry:
            failed.append({"id": eid, "reason": "凭证不存在"})
            continue
        if entry.status == "exported":
            failed.append({"id": eid, "reason": "已导出的凭证不可删除"})
            continue
        try:
            await entry_service.delete_entry(db, entry)
            deleted.append(eid)
        except Exception as e:
            failed.append({"id": eid, "reason": str(e)})
    return {"deleted": len(deleted), "failed": failed}


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(entry_id: str, db: AsyncSession = Depends(get_db)):
    entry = await entry_service.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="凭证不存在")
    if entry.status == "exported":
        raise HTTPException(status_code=400, detail="已导出的凭证不可删除")
    await entry_service.delete_entry(db, entry)
    return None
