"""Bank statement import API routes."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.services import bank_service
from app.schemas.journal_entry import EntryResponse

router = APIRouter(prefix="/api/v1/bank", tags=["bank"])


@router.post("/upload")
async def upload_bank_statement(
    file: UploadFile = File(..., description="银行流水文件 (CSV或Excel)"),
    client_id: str = Query(..., description="客户ID"),
    db: AsyncSession = Depends(get_db),
):
    """Parse a bank statement file and return matched transactions."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="无效文件")

    content = await file.read()
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    try:
        if ext in ("csv", "txt"):
            txns = bank_service.parse_bank_csv(content, file.filename)
        elif ext in ("xlsx", "xls"):
            txns = bank_service.parse_bank_excel(content, file.filename)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的文件格式: .{ext}，支持 CSV、Excel")
    except Exception as e:
        logger.error(f"Bank parse error: {e}")
        raise HTTPException(status_code=400, detail="文件解析失败，请检查格式是否正确")

    if not txns:
        raise HTTPException(status_code=400, detail="未能从文件中解析到交易记录，请检查文件格式")

    # Auto-match subjects
    txns = bank_service.match_transactions(txns)

    return {
        "filename": file.filename,
        "total": len(txns),
        "transactions": txns,
    }


class GenerateEntriesRequest(BaseModel):
    client_id: str
    transactions: list[dict]  # selected transactions with suggested codes
    voucher_date: date | None = None


@router.post("/generate")
async def generate_from_bank(
    data: GenerateEntriesRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate journal entries from selected bank transactions."""
    entries_created = []
    vdate = data.voucher_date or date.today()

    for txn in data.transactions:
        code = txn.get("suggested_code", "5602.99")
        name = txn.get("suggested_name", "管理费用-其他")
        direction = txn.get("suggested_dir", "debit")
        amount = float(txn.get("suggested_amount", 0))
        desc = txn.get("description", "")
        counterparty = txn.get("counterparty", "")
        income = float(txn.get("income", 0))
        expense = float(txn.get("expense", 0))

        if amount <= 0:
            continue

        # Build entry: matched account + 银行存款 on the other side
        entry_id = str(uuid.uuid4())
        entry = JournalEntry(
            id=entry_id,
            client_id=data.client_id,
            voucher_date=vdate,
            voucher_type="付" if direction == "debit" else "收",
            summary=f"银行流水: {desc}" + (f" ({counterparty})" if counterparty else ""),
            status="draft",
        )
        db.add(entry)

        # Line 1: matched account
        db.add(JournalEntryLine(
            id=str(uuid.uuid4()), entry_id=entry_id, line_number=1,
            account_code=code, account_name=name,
            direction=direction, amount=amount,
            summary_detail=desc,
        ))

        # Line 2: 银行存款 (opposite direction)
        bank_dir = "credit" if direction == "debit" else "debit"
        db.add(JournalEntryLine(
            id=str(uuid.uuid4()), entry_id=entry_id, line_number=2,
            account_code="1002", account_name="银行存款",
            direction=bank_dir, amount=amount,
            summary_detail="银行流水",
        ))

        entries_created.append(entry_id)

    await db.flush()
    return {"created": len(entries_created), "entry_ids": entries_created}
