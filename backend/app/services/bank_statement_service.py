"""Bank statement upload, AI extraction, and entry generation."""

import csv
import io
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from openpyxl import load_workbook
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.bank_statement import BankStatementTransaction, BankStatementUpload
from app.schemas.journal_entry import EntryCreate, EntryLineCreate
from app.services.ai_service import ai_service, extract_text
from app.services.entry_service import create_entry


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = re.sub(r"[^\d.\-]", "", str(value).replace(",", "")).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    text = str(value).strip().replace("/", "-").replace(".", "-")
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y%m%d"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            continue
    return None


def _rows_to_text(rows: list[list[Any]]) -> str:
    return "\n".join("\t".join("" if c is None else str(c) for c in row) for row in rows)


def _guess_subject(
    summary: str | None,
    counterparty: str | None,
    is_income: bool,
) -> tuple[str, str, str]:
    text = f"{summary or ''} {counterparty or ''}".lower()
    rules = [
        (("手续费", "账户管理", "网银", "电子汇划费", "短信费"), "5603.02", "财务费用-手续费", "银行费用"),
        (("利息",), "5603.03" if is_income else "5603.01", "财务费用-利息收入" if is_income else "财务费用-利息支出", "利息收支"),
        (("工资", "薪酬", "代发"), "2211.01", "应付职工薪酬-工资", "工资薪酬"),
        (("社保", "养老", "医保"), "2211.02", "应付职工薪酬-社保", "社保款项"),
        (("公积金",), "2211.03", "应付职工薪酬-公积金", "公积金款项"),
        (("税", "税费", "国库"), "2221", "应交税费", "税费缴纳"),
        (("办公", "文具", "打印", "耗材"), "5602.02", "管理费用-办公费", "办公支出"),
        (("餐", "饭", "招待", "宴请"), "5602.05", "管理费用-业务招待费", "餐饮招待"),
        (("差旅", "住宿", "酒店", "机票", "火车", "打车"), "5602.04", "管理费用-差旅费", "差旅出行"),
        (("加油", "停车", "etc", "过路"), "5602.03", "管理费用-交通费", "交通车辆"),
        (("租金", "房租", "租赁"), "5602.08", "管理费用-租赁费", "租赁支出"),
        (("软件", "平台", "技术服务", "saas"), "5602.11", "管理费用-软件服务费", "软件技术服务"),
        (("咨询", "审计", "律师", "代理记账", "知识产权"), "5602.10", "管理费用-中介咨询费", "专业服务"),
    ]
    for keywords, code, name, reason in rules:
        if any(keyword in text for keyword in keywords):
            return code, name, reason
    if is_income:
        return "5001", "主营业务收入", "银行流水收入，待人工确认"
    return "5602.99", "管理费用-其他", "银行流水支出，待人工确认"


def _parse_transaction_rows(rows: list[list[Any]]) -> list[dict[str, Any]]:
    """Parse common bank export rows by column position and typed values."""
    transactions: list[dict[str, Any]] = []
    for row in rows:
        if len(row) < 4:
            continue
        tx_date = _to_date(row[0])
        if not tx_date:
            continue

        expense = _to_float(row[2] if len(row) > 2 else None)
        income = _to_float(row[3] if len(row) > 3 else None)
        if not expense and not income:
            continue

        balance = _to_float(row[4] if len(row) > 4 else None)
        account_number = str(row[5]).strip() if len(row) > 5 and row[5] not in (None, "") else None
        counterparty = str(row[6]).strip() if len(row) > 6 and row[6] not in (None, "") else None
        summary = str(row[7]).strip() if len(row) > 7 and row[7] not in (None, "") else None
        code, name, reason = _guess_subject(summary, counterparty, bool(income))

        transactions.append({
            "transaction_date": tx_date.isoformat(),
            "summary": summary,
            "counterparty": counterparty,
            "account_number": account_number,
            "income_amount": income,
            "expense_amount": expense,
            "balance": balance,
            "suggested_subject_code": code,
            "suggested_subject_name": name,
            "subject_reason": reason,
            "confidence": 72,
            "source": "spreadsheet",
        })
    return transactions


def _extract_spreadsheet(path: Path) -> tuple[str, list[dict[str, Any]]]:
    if path.suffix.lower() == ".csv":
        raw = path.read_bytes()
        for enc in ("utf-8-sig", "gbk", "utf-8"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode("utf-8", errors="ignore")
        rows = list(csv.reader(io.StringIO(text)))
        return _rows_to_text(rows[:500]), _parse_transaction_rows(rows)

    wb = load_workbook(path, read_only=True, data_only=True)
    rows: list[list[Any]] = []
    try:
        for ws in wb.worksheets:
            rows.append([f"工作表: {ws.title}"])
            for row in ws.iter_rows(max_row=500, values_only=True):
                if any(cell not in (None, "") for cell in row):
                    rows.append(list(row))
    finally:
        wb.close()
    return _rows_to_text(rows), _parse_transaction_rows(rows)


def _transaction_to_entry(
    tx: BankStatementTransaction,
    voucher_type: str = "记",
) -> EntryCreate | None:
    amount = float(tx.expense_amount or tx.income_amount or 0)
    if amount <= 0:
        return None

    bank_code = "1002"
    bank_name = "银行存款"
    subject_code = tx.suggested_subject_code or "5602.99"
    subject_name = tx.suggested_subject_name or "管理费用-其他"
    summary = tx.summary or tx.counterparty or "银行流水"
    if tx.counterparty and tx.counterparty not in summary:
        summary = f"{summary} - {tx.counterparty}"

    if tx.expense_amount:
        lines = [
            EntryLineCreate(
                line_number=1,
                account_code=subject_code,
                account_name=subject_name,
                direction="debit",
                amount=round(amount, 2),
                summary_detail=tx.summary,
            ),
            EntryLineCreate(
                line_number=2,
                account_code=bank_code,
                account_name=bank_name,
                direction="credit",
                amount=round(amount, 2),
                summary_detail=tx.counterparty,
            ),
        ]
    else:
        lines = [
            EntryLineCreate(
                line_number=1,
                account_code=bank_code,
                account_name=bank_name,
                direction="debit",
                amount=round(amount, 2),
                summary_detail=tx.counterparty,
            ),
            EntryLineCreate(
                line_number=2,
                account_code=subject_code,
                account_name=subject_name,
                direction="credit",
                amount=round(amount, 2),
                summary_detail=tx.summary,
            ),
        ]

    return EntryCreate(
        client_id=tx.client_id,
        voucher_date=tx.transaction_date or date.today(),
        voucher_type=voucher_type,
        summary=summary[:500],
        lines=lines,
    )


async def upload_and_extract(
    db: AsyncSession,
    file: UploadFile,
    client_id: str,
    auto_generate: bool = False,
) -> tuple[BankStatementUpload, list[str]]:
    upload_id = str(uuid.uuid4())
    original_filename = file.filename or "bank-statement.xlsx"
    ext = Path(original_filename).suffix.lower() or ".xlsx"
    save_name = f"{upload_id}{ext}"
    upload_path = settings.upload_path / save_name
    content = await file.read()
    upload_path.write_bytes(content)

    upload = BankStatementUpload(
        id=upload_id,
        client_id=client_id,
        file_path=str(upload_path),
        filename=original_filename,
        status="pending",
    )
    db.add(upload)
    await db.flush()

    try:
        local_transactions: list[dict[str, Any]] = []
        if ext in {".csv", ".xlsx", ".xlsm"}:
            text, local_transactions = _extract_spreadsheet(upload_path)
        else:
            text = extract_text(upload_path)
        upload.raw_text = text[:60000]

        if settings.deepseek_api_key:
            result = await ai_service.extract_bank_statement(text)
        else:
            result = {
                "warning": "未配置DEEPSEEK_API_KEY，已使用本地规则解析流水，AI科目推荐未启用",
                "transactions": local_transactions,
            }
        upload.raw_ai_response = result
        if "error" in result and not local_transactions:
            upload.status = "failed"
            upload.error_msg = result["error"]
            await db.flush()
            return await get_upload(db, upload.id), []
        if "error" in result and local_transactions:
            result = {
                "warning": result["error"],
                "transactions": local_transactions,
            }
            upload.raw_ai_response = result

        transactions = result.get("transactions") or local_transactions
        if not transactions:
            upload.status = "failed"
            upload.error_msg = "未识别到银行流水明细"
            await db.flush()
            return await get_upload(db, upload.id), []

        for item in transactions:
            income = _to_float(item.get("income_amount"))
            expense = _to_float(item.get("expense_amount"))
            income = abs(income) if income else None
            expense = abs(expense) if expense else None
            if income and expense:
                if abs(income) >= abs(expense):
                    expense = None
                else:
                    income = None

            tx = BankStatementTransaction(
                id=str(uuid.uuid4()),
                upload_id=upload.id,
                client_id=client_id,
                transaction_date=_to_date(item.get("transaction_date")),
                summary=item.get("summary"),
                counterparty=item.get("counterparty"),
                account_number=item.get("account_number"),
                income_amount=income,
                expense_amount=expense,
                balance=_to_float(item.get("balance")),
                suggested_subject_code=item.get("suggested_subject_code"),
                suggested_subject_name=item.get("suggested_subject_name"),
                subject_reason=item.get("subject_reason"),
                confidence=_to_float(item.get("confidence")),
                status="recognized" if (income or expense) else "failed",
                error_msg=None if (income or expense) else "未识别到交易金额",
                raw_data=item,
            )
            db.add(tx)

        upload.status = "done"
        await db.flush()
    except Exception as e:
        upload.status = "failed"
        upload.error_msg = str(e)
        await db.flush()
        return await get_upload(db, upload.id), []

    entry_ids: list[str] = []
    upload = await get_upload(db, upload.id)
    if auto_generate:
        for tx in upload.transactions:
            if tx.status != "recognized" or tx.entry_id:
                continue
            entry_data = _transaction_to_entry(tx)
            if not entry_data:
                continue
            entry = await create_entry(db, entry_data)
            tx.entry_id = entry.id
            entry_ids.append(entry.id)
        await db.flush()
        upload = await get_upload(db, upload.id)

    return upload, entry_ids


async def list_uploads(
    db: AsyncSession,
    client_id: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
):
    stmt = select(BankStatementUpload).options(
        selectinload(BankStatementUpload.transactions)
    )
    if client_id:
        stmt = stmt.where(BankStatementUpload.client_id == client_id)
    if status:
        stmt = stmt.where(BankStatementUpload.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(BankStatementUpload.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.unique().scalars().all(), total


async def get_upload(db: AsyncSession, upload_id: str) -> BankStatementUpload | None:
    stmt = (
        select(BankStatementUpload)
        .options(selectinload(BankStatementUpload.transactions))
        .where(BankStatementUpload.id == upload_id)
    )
    result = await db.execute(stmt)
    return result.unique().scalar_one_or_none()


async def get_transaction(
    db: AsyncSession, transaction_id: str
) -> BankStatementTransaction | None:
    stmt = select(BankStatementTransaction).where(
        BankStatementTransaction.id == transaction_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def generate_entry_for_transaction(
    db: AsyncSession, tx: BankStatementTransaction
) -> str:
    if tx.entry_id:
        return tx.entry_id
    entry_data = _transaction_to_entry(tx)
    if not entry_data:
        raise ValueError("该流水无法生成凭证")
    entry = await create_entry(db, entry_data)
    tx.entry_id = entry.id
    await db.flush()
    return entry.id
