"""Entry template service — CRUD + apply to create journal entry."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.entry_template import EntryTemplate, EntryTemplateLine
from app.models.journal_entry import JournalEntry, JournalEntryLine
from app.schemas.journal_entry import EntryCreate, EntryLineCreate


async def list_templates(
    db: AsyncSession,
    client_id: str | None = None,
) -> list[EntryTemplate]:
    stmt = (
        select(EntryTemplate)
        .options(selectinload(EntryTemplate.lines))
        .where(EntryTemplate.is_active == True)
    )
    if client_id:
        stmt = stmt.where(
            (EntryTemplate.client_id == None) | (EntryTemplate.client_id == client_id)
        )
    else:
        stmt = stmt.where(EntryTemplate.client_id == None)
    stmt = stmt.order_by(EntryTemplate.sort_order, EntryTemplate.name)
    result = await db.execute(stmt)
    return list(result.unique().scalars().all())


async def get_template(db: AsyncSession, template_id: str) -> EntryTemplate | None:
    stmt = (
        select(EntryTemplate)
        .options(selectinload(EntryTemplate.lines))
        .where(EntryTemplate.id == template_id)
    )
    result = await db.execute(stmt)
    return result.unique().scalar_one_or_none()


async def apply_template(
    db: AsyncSession,
    template_id: str,
    client_id: str,
    voucher_date: date,
    summary: str | None = None,
    amounts: dict[int, float] | None = None,
) -> JournalEntry:
    """Apply a template to create a real journal entry."""
    template = await get_template(db, template_id)
    if not template:
        raise ValueError("模板不存在")

    # Build summary
    final_summary = summary or template.summary_template
    month_str = f"{voucher_date.month}月"
    final_summary = final_summary.replace("{month}", month_str).replace("{date}", voucher_date.isoformat())

    lines: list[EntryLineCreate] = []
    for i, tl in enumerate(template.lines):
        # Determine amount
        if tl.amount_source == "fixed" and tl.fixed_amount:
            amt = tl.fixed_amount
        elif amounts and tl.line_number in amounts:
            amt = amounts[tl.line_number]
        else:
            continue  # Skip lines without amount (manual but not provided)

        if amt <= 0:
            continue

        lines.append(EntryLineCreate(
            line_number=i + 1,
            account_code=tl.account_code,
            account_name=tl.account_name,
            direction=tl.direction,
            amount=round(amt, 2),
            summary_detail=tl.summary_detail or "",
        ))

    if len(lines) < 2:
        raise ValueError("模板至少需要 2 行有效分录")

    entry = JournalEntry(
        id=str(uuid.uuid4()),
        client_id=client_id,
        voucher_date=voucher_date,
        voucher_type=template.voucher_type,
        summary=final_summary,
        status="draft",
    )
    db.add(entry)

    for ld in lines:
        db.add(JournalEntryLine(
            id=str(uuid.uuid4()),
            entry_id=entry.id,
            line_number=ld.line_number,
            account_code=ld.account_code,
            account_name=ld.account_name,
            direction=ld.direction,
            amount=ld.amount,
            summary_detail=ld.summary_detail,
        ))

    await db.flush()
    return entry


async def create_template(
    db: AsyncSession,
    name: str,
    summary_template: str,
    lines_data: list[dict],
    client_id: str | None = None,
    voucher_type: str = "记",
) -> EntryTemplate:
    tpl = EntryTemplate(
        id=str(uuid.uuid4()),
        client_id=client_id,
        name=name,
        summary_template=summary_template,
        voucher_type=voucher_type,
    )
    db.add(tpl)
    for ld in lines_data:
        db.add(EntryTemplateLine(
            id=str(uuid.uuid4()),
            template_id=tpl.id,
            line_number=ld["line_number"],
            account_code=ld["account_code"],
            account_name=ld["account_name"],
            direction=ld["direction"],
            amount_source=ld.get("amount_source", "fixed"),
            fixed_amount=ld.get("fixed_amount"),
            summary_detail=ld.get("summary_detail"),
        ))
    await db.flush()
    return tpl


async def delete_template(db: AsyncSession, template: EntryTemplate):
    template.is_active = False
    await db.flush()
