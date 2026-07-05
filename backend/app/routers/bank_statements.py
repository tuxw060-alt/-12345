"""Bank statement API routes."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.bank_statement import (
    BankStatementListResponse,
    BankStatementUploadResponse,
    BankStatementUploadResult,
)
from app.services import bank_statement_service

router = APIRouter(prefix="/api/v1/bank-statements", tags=["bank-statements"])


class EntryIdResponse(BaseModel):
    entry_id: str


class BatchDeleteRequest(BaseModel):
    upload_ids: list[str]


class BatchDeleteResponse(BaseModel):
    deleted: int
    failed: list[dict] = []


class GenerateEntriesRequest(BaseModel):
    client_id: str


class GenerateEntriesResponse(BaseModel):
    entry_ids: list[str]
    generated: int


class AccountSelectionRequest(BaseModel):
    account_code: str
    account_name: str
    account_full_name: str | None = None
    parent_account_code: str | None = None
    parent_account_name: str | None = None
    source: str = "manual"


class TemplateSelectionRequest(BaseModel):
    document_type_id: str | None = None
    document_name: str | None = None
    settlement_method: str | None = None
    business_type: str | None = None
    template_id: str | None = None


@router.post("/upload", response_model=BankStatementUploadResult, status_code=201)
async def upload_bank_statement(
    file: UploadFile = File(..., description="bank statement file"),
    client_id: str = Query(..., description="client id"),
    auto_generate: bool = Query(False, description="create voucher draft after recognition"),
    db: AsyncSession = Depends(get_db),
):
    allowed = {".csv", ".xlsx", ".xlsm", ".ods", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".pdf"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported file extension: {ext}; allowed: {', '.join(sorted(allowed))}",
        )

    upload, entry_ids = await bank_statement_service.upload_and_extract(
        db, file, client_id, auto_generate=auto_generate
    )
    return BankStatementUploadResult(
        upload=BankStatementUploadResponse.model_validate(upload),
        entry_ids=entry_ids,
    )


@router.get("", response_model=BankStatementListResponse)
async def list_bank_statement_uploads(
    client_id: str | None = Query(None),
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    items, total = await bank_statement_service.list_uploads(
        db, client_id=client_id, status=status, offset=offset, limit=limit
    )
    return BankStatementListResponse(
        items=[BankStatementUploadResponse.model_validate(item) for item in items],
        total=total,
    )


@router.post("/batch-delete", response_model=BatchDeleteResponse)
async def batch_delete_uploads(
    data: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    deleted = 0
    failed: list[dict] = []
    seen_ids: set[str] = set()
    for upload_id in data.upload_ids:
        if upload_id in seen_ids:
            continue
        seen_ids.add(upload_id)
        upload = await bank_statement_service.get_upload(db, upload_id)
        if not upload:
            failed.append({"id": upload_id, "reason": "upload not found"})
            continue
        try:
            await bank_statement_service.delete_upload(db, upload)
            deleted += 1
        except Exception as exc:
            failed.append({"id": upload_id, "reason": str(exc)})
    return BatchDeleteResponse(deleted=deleted, failed=failed)


@router.post("/generate-entries", response_model=GenerateEntriesResponse)
async def generate_entries(
    data: GenerateEntriesRequest,
    db: AsyncSession = Depends(get_db),
):
    entry_ids = await bank_statement_service.generate_entries_for_client(db, data.client_id)
    return GenerateEntriesResponse(entry_ids=entry_ids, generated=len(entry_ids))


@router.post("/transactions/{transaction_id}/generate-entry", response_model=EntryIdResponse)
async def generate_entry(transaction_id: str, db: AsyncSession = Depends(get_db)):
    tx = await bank_statement_service.get_transaction(db, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction not found")
    if tx.status != "recognized":
        raise HTTPException(status_code=400, detail=tx.error_msg or "transaction not recognized")
    try:
        entry_id = await bank_statement_service.generate_entry_for_transaction(db, tx)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EntryIdResponse(entry_id=entry_id)


@router.patch("/transactions/{transaction_id}/account-selection")
async def update_transaction_account_selection(
    transaction_id: str,
    data: AccountSelectionRequest,
    db: AsyncSession = Depends(get_db),
):
    tx = await bank_statement_service.get_transaction(db, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction not found")
    tx = await bank_statement_service.update_transaction_account_selection(
        db,
        tx,
        account_code=data.account_code,
        account_name=data.account_name,
        account_full_name=data.account_full_name,
        parent_account_code=data.parent_account_code,
        parent_account_name=data.parent_account_name,
        source=data.source,
    )
    return {"ok": True, "transaction_id": tx.id}


@router.patch("/transactions/{transaction_id}/template-selection")
async def update_transaction_template_selection(
    transaction_id: str,
    data: TemplateSelectionRequest,
    db: AsyncSession = Depends(get_db),
):
    tx = await bank_statement_service.get_transaction(db, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction not found")
    tx = await bank_statement_service.update_transaction_template_selection(
        db,
        tx,
        document_type_id=data.document_type_id,
        document_name=data.document_name,
        settlement_method=data.settlement_method,
        business_type=data.business_type,
        template_id=data.template_id,
    )
    return {"ok": True, "transaction_id": tx.id, "template_id": tx.selected_template_id}
