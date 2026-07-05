"""JournalEntry CRUD service."""

import uuid
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.models.account_subject import AccountSubject
from app.schemas.journal_entry import EntryCreate, EntryUpdate

# Parent-level 往来科目 — 不能直接用于凭证
PARENT_RECEIVABLE_CODES = {"1122", "1123", "1221", "2202", "2203", "2241"}


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

    return items, total


async def get_entry(db: AsyncSession, entry_id: str) -> JournalEntry | None:
    stmt = (
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == entry_id)
    )
    result = await db.execute(stmt)
    return result.unique().scalar_one_or_none()


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
    )
    db.add(entry)

    for line_data in data.lines:
        line = JournalEntryLine(
            id=str(uuid.uuid4()),
            entry_id=entry.id,
            line_number=line_data.line_number,
            account_code=line_data.account_code,
            account_name=line_data.account_name,
            direction=line_data.direction,
            amount=line_data.amount,
            summary_detail=line_data.summary_detail,
            manual_account_override=getattr(line_data, 'manual_account_override', False),
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
                line_number=line_data.line_number,
                account_code=line_data.account_code,
                account_name=line_data.account_name,
                direction=line_data.direction,
                amount=line_data.amount,
                summary_detail=line_data.summary_detail,
                manual_account_override=getattr(line_data, 'manual_account_override', False),
            )
            db.add(line)

    await db.flush()
    # Reload to get updated lines
    return await get_entry(db, entry.id)


async def confirm_entry(db: AsyncSession, entry: JournalEntry) -> JournalEntry:
    """Confirm a draft entry after running validation checks."""
    errors = await _validate_entry_for_confirm(db, entry)
    if errors:
        raise ValueError("; ".join(errors))

    entry.status = "confirmed"
    entry.updated_at = datetime.now()
    await db.flush()
    return await get_entry(db, entry.id)


async def _validate_entry_for_confirm(db: AsyncSession, entry: JournalEntry) -> list[str]:
    """Validate a journal entry before confirming. Returns error messages (empty=valid)."""
    errors: list[str] = []

    # 1. Balance check
    debit_total = sum(l.amount for l in entry.lines if l.direction == "debit")
    credit_total = sum(l.amount for l in entry.lines if l.direction == "credit")
    diff = round(debit_total - credit_total, 2)
    if abs(diff) > 0.01:
        errors.append(
            f"借贷不平衡：借方¥{debit_total:.2f}，贷方¥{credit_total:.2f}，"
            f"差额¥{abs(diff):.2f}，不能确认凭证"
        )

    for line in entry.lines:
        prefix = f"第{line.line_number}行"

        # 2. Empty account code
        if not line.account_code or line.account_code.strip() == "":
            errors.append(f"{prefix}科目为空，不能确认")
            continue

        # 3. Pending account
        if line.account_code == "PENDING":
            errors.append(f"{prefix}待选择科目，不能确认凭证")
            continue

        # 4. Look up subject
        stmt = select(AccountSubject).where(
            AccountSubject.code == line.account_code,
            AccountSubject.is_active == True,
        )
        result = await db.execute(stmt)
        subject = result.scalar_one_or_none()

        if not subject:
            errors.append(f"{prefix}科目 {line.account_code} 不存在或已停用，不能确认")
            continue

        # 5. Non-leaf subject check
        if not subject.is_leaf:
            errors.append(
                f"{prefix}科目「{subject.full_name or subject.name}」不是末级科目，不能直接做账"
            )

        # 6. Parent-level receivable/payable check
        clean_code = line.account_code.split(".")[0] if "." in line.account_code else line.account_code
        # Also check full code match
        if line.account_code in PARENT_RECEIVABLE_CODES:
            errors.append(
                f"{prefix}仍使用父级往来科目 {line.account_code}「{line.account_name}」，"
                f"请选择客户/供应商明细"
            )
        elif clean_code in PARENT_RECEIVABLE_CODES and not subject.is_leaf:
            errors.append(
                f"{prefix}科目「{subject.full_name or subject.name}」为非末级往来科目，请选择明细"
            )

    return errors


async def delete_entry(db: AsyncSession, entry: JournalEntry) -> None:
    await db.delete(entry)
    await db.flush()
