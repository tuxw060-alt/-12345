"""JournalEntry CRUD service."""

import uuid
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import inspect, select, func, update
from sqlalchemy.orm import selectinload

from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.bank_statement import BankStatementTransaction
from app.models.account_subject import AccountSubject
from app.schemas.journal_entry import EntryCreate, EntryUpdate
from app.services.subject_service import (
    find_legacy_sub_account_by_counterparty,
    legacy_subject_line_fields,
)


class EntryValidationError(ValueError):
    pass


CURRENT_PARENT_CODES = {"1122", "1123", "1221", "2202", "2203", "2241"}


def _allowed_parent_codes_for_line(account_code: str | None) -> list[str]:
    code = (account_code or "").strip()
    preferred = [code] if code in CURRENT_PARENT_CODES else []
    return list(dict.fromkeys([*preferred, "2241", "1221", "2202", "1122", "2203", "1123"]))


async def repair_voucher_line_legacy_account(
    db: AsyncSession,
    *,
    client_id: str,
    line: JournalEntryLine,
) -> bool:
    if line.manual_account_override:
        return False
    if (line.account_code or "").strip() not in CURRENT_PARENT_CODES:
        return False
    party = (line.auxiliary_name or line.counterparty_name or "").strip()
    if not party:
        return False
    matched = await find_legacy_sub_account_by_counterparty(
        db,
        client_id=client_id,
        counterparty_name=party,
        allowed_parent_codes=_allowed_parent_codes_for_line(line.account_code),
    )
    if not matched:
        return False
    fields = legacy_subject_line_fields(matched, is_income=line.direction == "credit")
    line.account_code = str(fields["account_code"] or line.account_code)
    line.account_name = str(fields["account_name"] or line.account_name)
    line.account_full_name = fields["account_full_name"]
    line.parent_account_code = fields["parent_account_code"]
    line.parent_account_name = fields["parent_account_name"]
    line.auxiliary_type = fields["auxiliary_type"]
    line.auxiliary_code = fields["auxiliary_code"]
    line.auxiliary_name = fields["auxiliary_name"]
    line.counterparty_name = line.counterparty_name or party
    return True


async def repair_entry_legacy_accounts(db: AsyncSession, entry: JournalEntry | None) -> bool:
    if not entry or entry.status != "draft":
        return False
    changed = False
    if "lines" in inspect(entry).unloaded:
        result = await db.execute(
            select(JournalEntryLine)
            .where(JournalEntryLine.entry_id == entry.id)
            .order_by(JournalEntryLine.line_number)
        )
        lines = list(result.scalars().all())
    else:
        lines = list(entry.lines)
    for line in lines:
        changed = await repair_voucher_line_legacy_account(
            db,
            client_id=entry.client_id,
            line=line,
        ) or changed
    if changed:
        await db.flush()
    return changed


async def _entry_lines(db: AsyncSession, entry: JournalEntry) -> list[JournalEntryLine]:
    if "lines" not in inspect(entry).unloaded:
        return list(entry.lines)
    result = await db.execute(
        select(JournalEntryLine)
        .where(JournalEntryLine.entry_id == entry.id)
        .order_by(JournalEntryLine.line_number)
    )
    return list(result.scalars().all())


def _line_values(line_data) -> dict:
    debit_value = round(float(line_data.debitAmount or 0), 2)
    credit_value = round(float(line_data.creditAmount or 0), 2)
    amount = credit_value if line_data.direction == "credit" else debit_value
    return {
        "line_number": line_data.line_number,
        "account_code": line_data.account_code,
        "account_name": line_data.account_name,
        "direction": line_data.direction,
        "amount": amount,
        "summary_detail": line_data.summary_detail,
        "account_full_name": line_data.account_full_name,
        "parent_account_code": line_data.parent_account_code,
        "parent_account_name": line_data.parent_account_name,
        "auxiliary_type": line_data.auxiliary_type,
        "auxiliary_code": line_data.auxiliary_code,
        "auxiliary_name": line_data.auxiliary_name,
        "counterparty_name": line_data.counterparty_name,
        "counterparty_account": line_data.counterparty_account,
        "source_type": line_data.source_type,
        "source_document_id": line_data.source_document_id,
        "source_row_id": line_data.source_row_id,
        "manual_account_override": line_data.manual_account_override,
        "account_selection_source": line_data.account_selection_source or "auto",
    }


async def list_entries(
    db: AsyncSession,
    client_id: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    offset: int = 0,
    limit: int = 50,
):
    stmt = select(JournalEntry).options(selectinload(JournalEntry.lines))

    if client_id:
        stmt = stmt.where(JournalEntry.client_id == client_id)
    if status:
        stmt = stmt.where(JournalEntry.status == status)
    if date_from:
        stmt = stmt.where(JournalEntry.voucher_date >= date_from)
    if date_to:
        stmt = stmt.where(JournalEntry.voucher_date <= date_to)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(JournalEntry.voucher_date.desc(), JournalEntry.created_at.desc())
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = result.unique().scalars().all()
    for entry in items:
        await repair_entry_legacy_accounts(db, entry)

    return items, total


async def get_entry(db: AsyncSession, entry_id: str) -> JournalEntry | None:
    stmt = (
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == entry_id)
    )
    result = await db.execute(stmt)
    entry = result.unique().scalar_one_or_none()
    await repair_entry_legacy_accounts(db, entry)
    return entry


async def create_entry(db: AsyncSession, data: EntryCreate) -> JournalEntry:
    entry = JournalEntry(
        id=str(uuid.uuid4()),
        client_id=data.client_id,
        source_invoice_id=data.source_invoice_id,
        voucher_date=data.voucher_date,
        voucher_type=data.voucher_type,
        voucher_number=data.voucher_number,
        summary=data.summary,
        status="draft",
        source_row_ids=data.sourceRowIds or None,
    )
    db.add(entry)

    for line_data in data.lines:
        line = JournalEntryLine(
            id=str(uuid.uuid4()),
            entry_id=entry.id,
            **_line_values(line_data),
        )
        db.add(line)

    await db.flush()
    # Re-fetch with eager-load to avoid greenlet issues
    return await get_entry(db, entry.id)


async def update_entry(
    db: AsyncSession, entry: JournalEntry, data: EntryUpdate
) -> JournalEntry:
    # Update header fields
    for field in ("voucher_date", "voucher_type", "voucher_number", "summary"):
        value = getattr(data, field, None)
        if value is not None:
            setattr(entry, field, value)
    if data.sourceRowIds is not None:
        entry.source_row_ids = data.sourceRowIds or None

    # Update lines: delete old, insert new
    if data.lines is not None:
        # Delete old lines
        for line in entry.lines:
            await db.delete(line)
        # Add new lines
        for line_data in data.lines:
            line = JournalEntryLine(
                id=str(uuid.uuid4()),
                entry_id=entry.id,
                **_line_values(line_data),
            )
            db.add(line)

    await db.flush()
    # Reload to get updated lines
    return await get_entry(db, entry.id)


async def validate_entry_for_confirm(db: AsyncSession, entry: JournalEntry) -> None:
    lines = await _entry_lines(db, entry)
    subject_codes = [line.account_code.strip() for line in lines if (line.account_code or "").strip()]
    subject_status: dict[str, bool] = {}
    if subject_codes:
        result = await db.execute(
            select(AccountSubject.code, AccountSubject.is_active).where(
                AccountSubject.code.in_(subject_codes),
                (AccountSubject.client_id == entry.client_id) | (AccountSubject.client_id == None),
            )
        )
        for code, is_active in result.all():
            subject_status[code] = bool(is_active)

    effective_lines = [
        line for line in lines
        if (line.summary_detail or line.account_code or line.account_name or float(line.amount or 0) > 0)
    ]
    if len(effective_lines) < 2:
        raise EntryValidationError("at least two valid voucher lines are required")

    for line in effective_lines:
        code = (line.account_code or "").strip()
        name = (line.account_name or "").strip()
        if not (line.summary_detail or entry.summary or "").strip():
            raise EntryValidationError(f"Line {line.line_number} is missing summary")
        if not code or not name:
            raise EntryValidationError(f"Line {line.line_number} is missing account")
        if code == "PENDING" or name == "待选择科目":
            raise EntryValidationError(f"Line {line.line_number} still uses a pending account; choose a subject before confirming")
        if code in subject_status and not subject_status[code]:
            raise EntryValidationError(f"Line {line.line_number} uses a disabled account")
        if code in CURRENT_PARENT_CODES:
            raise EntryValidationError(f"Line {line.line_number} uses a parent current account; choose a sub-account")
        if code.startswith(("1122", "1123")) and not (line.auxiliary_name or "").strip():
            raise EntryValidationError(f"Line {line.line_number} receivable account is missing customer detail")
        if code.startswith(("2202", "2203")) and not (line.auxiliary_name or "").strip():
            raise EntryValidationError(f"Line {line.line_number} payable account is missing supplier detail")
        if line.direction not in {"debit", "credit"}:
            raise EntryValidationError(f"Line {line.line_number} has invalid debit/credit direction")
        if float(line.amount or 0) <= 0:
            raise EntryValidationError(f"Line {line.line_number} amount must be greater than 0")

    debit_total = sum(float(line.amount or 0) for line in lines if line.direction == "debit")
    credit_total = sum(float(line.amount or 0) for line in lines if line.direction == "credit")
    if max(debit_total, credit_total) <= 0:
        raise EntryValidationError("total amount must be greater than 0")
    if abs(debit_total - credit_total) >= 0.01:
        raise EntryValidationError("debit and credit totals are not balanced")

    if entry.voucher_number:
        month_start = entry.voucher_date.replace(day=1)
        if entry.voucher_date.month == 12:
            month_end = entry.voucher_date.replace(year=entry.voucher_date.year + 1, month=1, day=1)
        else:
            month_end = entry.voucher_date.replace(month=entry.voucher_date.month + 1, day=1)
        stmt = (
            select(JournalEntry)
            .where(JournalEntry.id != entry.id)
            .where(JournalEntry.client_id == entry.client_id)
            .where(JournalEntry.voucher_type == entry.voucher_type)
            .where(JournalEntry.voucher_number == entry.voucher_number)
            .where(JournalEntry.voucher_date >= month_start)
            .where(JournalEntry.voucher_date < month_end)
        )
        duplicate = (await db.execute(stmt)).scalar_one_or_none()
        if duplicate:
            raise EntryValidationError("voucher number already exists in this period")

async def confirm_entry(db: AsyncSession, entry: JournalEntry) -> JournalEntry:
    await repair_entry_legacy_accounts(db, entry)
    await validate_entry_for_confirm(db, entry)
    entry.status = "confirmed"
    now = datetime.now()
    entry.confirmed_at = now
    entry.updated_at = now
    await db.flush()
    # Re-fetch with eager-loaded lines to avoid greenlet issues
    return await get_entry(db, entry.id)


async def delete_entry(db: AsyncSession, entry: JournalEntry) -> None:
    await db.execute(
        update(BankStatementTransaction)
        .where(BankStatementTransaction.entry_id == entry.id)
        .values(entry_id=None, status="recognized")
    )
    await db.delete(entry)
    await db.flush()

