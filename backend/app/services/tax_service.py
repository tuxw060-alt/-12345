"""Tax calculation service — compute tax liabilities from journal entries."""

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.journal_entry import JournalEntry


async def get_tax_summary(
    db: AsyncSession,
    client_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """Calculate tax liabilities for a client in a given period."""

    stmt = (
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.client_id == client_id)
        .where(JournalEntry.status.in_(["confirmed", "exported"]))
    )
    if date_from:
        stmt = stmt.where(JournalEntry.voucher_date >= date_from)
    if date_to:
        stmt = stmt.where(JournalEntry.voucher_date <= date_to)
    result = await db.execute(stmt)
    entries = result.unique().scalars().all()

    # Initialize tax buckets
    input_vat = 0.0      # 进项税额 (2221.01.01 debit)
    output_vat = 0.0     # 销项税额 (2221.01.02 credit)
    paid_vat = 0.0       # 已交税金 (2221.01.03 debit)
    income_tax = 0.0     # 企业所得税 (2221.03)
    personal_tax = 0.0   # 个人所得税 (2221.04)
    urban_tax = 0.0      # 城建税 (2221.05)
    edu_surcharge = 0.0  # 教育费附加 (2221.06)
    local_edu = 0.0      # 地方教育附加 (2221.07)
    stamp_tax = 0.0      # 印花税 (2221.08)

    # Revenue and expense totals for income tax estimation
    total_revenue = 0.0
    total_expense = 0.0

    for entry in entries:
        for line in entry.lines:
            code = line.account_code
            amt = float(line.amount)

            # VAT
            if code == "2221.01.01" and line.direction == "debit":
                input_vat += amt
            elif code == "2221.01.02" and line.direction == "credit":
                output_vat += amt
            elif code == "2221.01.03" and line.direction == "debit":
                paid_vat += amt

            # Other taxes (credit side = accrued/payable)
            elif code == "2221.03" and line.direction == "credit":
                income_tax += amt
            elif code == "2221.04" and line.direction == "credit":
                personal_tax += amt
            elif code == "2221.05" and line.direction == "credit":
                urban_tax += amt
            elif code == "2221.06" and line.direction == "credit":
                edu_surcharge += amt
            elif code == "2221.07" and line.direction == "credit":
                local_edu += amt
            elif code == "2221.08" and line.direction == "credit":
                stamp_tax += amt

            # Revenue/cost for income estimation
            if code.startswith("50") or code.startswith("51") or code.startswith("53"):
                if line.direction == "credit":
                    total_revenue += amt
                else:
                    total_revenue -= amt
            elif code.startswith("54") or code.startswith("56") or code.startswith("57"):
                if line.direction == "debit":
                    total_expense += amt
                else:
                    total_expense -= amt

    # Calculate VAT payable
    vat_payable = round(output_vat - input_vat - paid_vat, 2)

    # Estimate additional taxes (if not already recorded)
    estimated_urban = round(vat_payable * 0.07, 2) if urban_tax == 0 else urban_tax
    estimated_edu = round(vat_payable * 0.03, 2) if edu_surcharge == 0 else edu_surcharge
    estimated_local_edu = round(vat_payable * 0.02, 2) if local_edu == 0 else local_edu
    total_surcharges = round(estimated_urban + estimated_edu + estimated_local_edu, 2)

    # Estimate income tax (25% of profit, simplified)
    profit = round(total_revenue - total_expense, 2)
    estimated_income_tax = round(max(profit, 0) * 0.25, 2) if income_tax == 0 else income_tax

    return {
        "period": {"from": str(date_from) if date_from else None, "to": str(date_to) if date_to else None},
        "vat": {
            "input_vat": round(input_vat, 2),
            "output_vat": round(output_vat, 2),
            "paid_vat": round(paid_vat, 2),
            "payable": vat_payable,
        },
        "surcharges": {
            "urban_construction": estimated_urban,
            "education": estimated_edu,
            "local_education": estimated_local_edu,
            "total": total_surcharges,
        },
        "income_tax": {
            "revenue": round(total_revenue, 2),
            "expense": round(total_expense, 2),
            "profit": profit,
            "estimated_tax": estimated_income_tax,
            "recorded_tax": round(income_tax, 2),
        },
        "other_taxes": {
            "personal_income": round(personal_tax, 2),
            "stamp": round(stamp_tax, 2),
        },
        "total_tax_liability": round(
            max(vat_payable, 0) + total_surcharges + estimated_income_tax + personal_tax + stamp_tax, 2
        ),
    }
