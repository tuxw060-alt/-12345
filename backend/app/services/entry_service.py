"""JournalEntry CRUD service."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.schemas.journal_entry import EntryCreate, EntryUpdate


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
            )
            db.add(line)

    await db.flush()
    # Reload to get updated lines
    return await get_entry(db, entry.id)


async def confirm_entry(db: AsyncSession, entry: JournalEntry) -> JournalEntry:
    entry.status = "confirmed"
    from datetime import datetime
    entry.updated_at = datetime.now()
    await db.flush()
    # Re-fetch with eager-loaded lines to avoid greenlet issues
    return await get_entry(db, entry.id)


async def delete_entry(db: AsyncSession, entry: JournalEntry) -> None:
    await db.delete(entry)
    await db.flush()
