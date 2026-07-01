"""Bank statement import API routes."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from loguru import logger
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.services import bank_service, client_service
from app.services.ai_service import ai_service
from app.schemas.journal_entry import EntryResponse

router = APIRouter(prefix="/api/v1/bank", tags=["bank"])

MAX_UPLOAD_MB = 20


@router.post("/upload")
async def upload_bank_statement(
    file: UploadFile = File(..., max_size=MAX_UPLOAD_MB * 1024 * 1024, description="银行流水文件 (CSV或Excel)"),
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bank parse error: {e}")
        raise HTTPException(status_code=400, detail="文件解析失败，请检查格式是否正确")

    if not txns:
        raise HTTPException(status_code=400, detail="未能从文件中解析到交易记录，请检查文件格式")

    # Step 1: Keyword-based quick match
    txns = bank_service.match_transactions(txns)

    # Step 2: AI-enhanced matching via DeepSeek
    statement_text = "\n".join(
        f"{t['date']} | {t['description']} | 收入:{t['income']} | 支出:{t['expense']} | 对方:{t.get('counterparty','')}"
        for t in txns
    )
    try:
        ai_result = await ai_service.extract_bank_statement(statement_text)
        ai_txns = ai_result.get("transactions", [])
        # Merge AI suggestions into transactions
        for i, txn in enumerate(txns):
            if i < len(ai_txns) and ai_txns[i].get("confidence", 0) > 60:
                at = ai_txns[i]
                txn["suggested_code"] = at.get("suggested_subject_code", txn.get("suggested_code"))
                txn["suggested_name"] = at.get("suggested_subject_name", txn.get("suggested_name"))
                txn["subject_reason"] = at.get("subject_reason", "")
                txn["ai_confidence"] = at.get("confidence", 0)
                txn["auto_matched"] = True
        logger.info(f"AI enhanced {min(len(ai_txns), len(txns))} bank transactions")
    except Exception as e:
        logger.warning(f"AI bank matching skipped: {e}")

    return {"filename": file.filename, "total": len(txns), "transactions": txns}


class GenerateEntriesRequest(BaseModel):
    client_id: str
    transactions: list[dict]
    voucher_date: date | None = None

    @field_validator("transactions")
    @classmethod
    def validate_txns(cls, v):
        for txn in v:
            if not isinstance(txn.get("suggested_code"), str) or not txn["suggested_code"]:
                raise ValueError("每笔交易必须有 suggested_code")
            dir_val = txn.get("suggested_dir", "")
            if dir_val not in ("debit", "credit"):
                raise ValueError(f"suggested_dir 必须为 debit 或 credit，收到: {dir_val}")
        return v


def _safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (ValueError, TypeError):
        return default


@router.post("/generate")
async def generate_from_bank(
    data: GenerateEntriesRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate journal entries from selected bank transactions."""
    client = await client_service.get_client(db, data.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="客户不存在")

    entries_created = []
    vdate = data.voucher_date or date.today()

    for txn in data.transactions:
        code = txn.get("suggested_code", "5602.99")
        name = txn.get("suggested_name", "管理费用-其他")
        direction = txn.get("suggested_dir", "debit")
        amount = _safe_float(txn.get("suggested_amount", 0))
        desc = txn.get("description", "")
        counterparty = txn.get("counterparty", "")

        if amount <= 0:
            continue

        entry_id = str(uuid.uuid4())
        entry = JournalEntry(
            id=entry_id, client_id=data.client_id, voucher_date=vdate,
            voucher_type="付" if direction == "debit" else "收",
            summary=f"银行流水: {desc}" + (f" ({counterparty})" if counterparty else ""),
            status="draft",
        )
        db.add(entry)

        db.add(JournalEntryLine(
            id=str(uuid.uuid4()), entry_id=entry_id, line_number=1,
            account_code=code, account_name=name,
            direction=direction, amount=amount, summary_detail=desc,
        ))

        bank_dir = "credit" if direction == "debit" else "debit"
        db.add(JournalEntryLine(
            id=str(uuid.uuid4()), entry_id=entry_id, line_number=2,
            account_code="1002", account_name="银行存款",
            direction=bank_dir, amount=amount, summary_detail="银行流水",
        ))
        entries_created.append(entry_id)

    await db.flush()
    return {"created": len(entries_created), "entry_ids": entries_created}
