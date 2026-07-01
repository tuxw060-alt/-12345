"""
Kingdee ZhangWuYou (金蝶快记帐) Excel export service.

Generates Excel files compatible with 金蝶快记帐's "凭证引入" (voucher import) feature.

The template follows the standard format:
- Column headers must exactly match what 快记帐 expects
- 科目代码 must be stored as text (not number) in Excel
- Each row = one journal entry line
- Rows with same voucher number belong to the same voucher
"""

import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.config import settings
from app.models.journal_entry import JournalEntry, JournalEntryLine


# Kingdee column headers in exact order
KINGDEE_HEADERS = [
    "凭证日期",      # A: Voucher date
    "凭证字",        # B: Voucher type (记/收/付/转)
    "凭证号",        # C: Voucher number
    "摘要",          # D: Summary
    "科目代码",      # E: Account code (MUST be text format!)
    "科目名称",      # F: Account name
    "借方金额",      # G: Debit amount
    "贷方金额",      # H: Credit amount
    "币别",          # I: Currency
    "汇率",          # J: Exchange rate
    "原币金额",      # K: Original currency amount
    "数量",          # L: Quantity
    "单价",          # M: Unit price
    "核算类别",      # N: Auxiliary category
    "核算代码",      # O: Auxiliary code
    "核算名称",      # P: Auxiliary name
    "制单人",        # Q: Creator
    "审核人",        # R: Reviewer
    "备注",          # S: Notes
]


async def get_entries_for_export(
    db: AsyncSession,
    client_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str = "confirmed",
) -> list[JournalEntry]:
    """Fetch confirmed entries ready for export."""
    stmt = (
        select(JournalEntry)
        .where(JournalEntry.status == status)
        .order_by(JournalEntry.voucher_date, JournalEntry.created_at)
    )
    if client_id:
        stmt = stmt.where(JournalEntry.client_id == client_id)
    if date_from:
        stmt = stmt.where(JournalEntry.voucher_date >= date_from)
    if date_to:
        stmt = stmt.where(JournalEntry.voucher_date <= date_to)

    result = await db.execute(stmt)
    entries = result.scalars().all()

    # Eager-load lines
    for entry in entries:
        # Access lines to ensure they're loaded
        _ = entry.lines

    return list(entries)


def generate_kingdee_excel(
    entries: Sequence[JournalEntry],
    output_path: str | Path | None = None,
) -> Path:
    """
    Generate a Kingdee-compatible Excel file from journal entries.

    Args:
        entries: Confirmed journal entries with lines.
        output_path: Where to save the file. Auto-generates if None.

    Returns:
        Path to the generated .xlsx file.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "凭证"

    # === Styles ===
    header_font = Font(name="微软雅黑", bold=True, size=10)
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell_alignment = Alignment(horizontal="left", vertical="center")
    amount_alignment = Alignment(horizontal="right", vertical="center")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # === Write header row ===
    for col_idx, header in enumerate(KINGDEE_HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # === Write data rows ===
    row = 2
    for entry in entries:
        voucher_date_str = entry.voucher_date.isoformat() if entry.voucher_date else ""

        for line in entry.lines:
            ws.cell(row=row, column=1, value=voucher_date_str)
            ws.cell(row=row, column=2, value=entry.voucher_type)
            ws.cell(row=row, column=3, value=entry.voucher_number or "")
            ws.cell(row=row, column=4, value=entry.summary)

            # CRITICAL: 科目代码 must be text format in Excel
            account_cell = ws.cell(row=row, column=5, value=line.account_code)
            account_cell.number_format = "@"  # Text format

            ws.cell(row=row, column=6, value=line.account_name)

            # Debit / Credit amounts
            if line.direction == "debit":
                ws.cell(row=row, column=7, value=float(line.amount))
                ws.cell(row=row, column=8, value="")
            else:
                ws.cell(row=row, column=7, value="")
                ws.cell(row=row, column=8, value=float(line.amount))

            # Defaults
            ws.cell(row=row, column=9, value="人民币")
            ws.cell(row=row, column=10, value=1)
            ws.cell(row=row, column=11, value="")  # 原币金额 (same for RMB)
            ws.cell(row=row, column=12, value="")
            ws.cell(row=row, column=13, value="")
            ws.cell(row=row, column=14, value="")
            ws.cell(row=row, column=15, value="")
            ws.cell(row=row, column=16, value="")
            ws.cell(row=row, column=17, value="快记帐")
            ws.cell(row=row, column=18, value="")
            ws.cell(row=row, column=19, value="")

            # Apply styles to all cells in this row
            for col in range(1, len(KINGDEE_HEADERS) + 1):
                cell = ws.cell(row=row, column=col)
                cell.border = thin_border
                if col in (7, 8, 10, 11, 12, 13):
                    cell.alignment = amount_alignment
                else:
                    cell.alignment = cell_alignment
                cell.font = Font(name="微软雅黑", size=9)

            row += 1

    # === Column widths ===
    col_widths = {
        1: 13,   # 凭证日期
        2: 8,    # 凭证字
        3: 10,   # 凭证号
        4: 40,   # 摘要
        5: 15,   # 科目代码
        6: 25,   # 科目名称
        7: 15,   # 借方金额
        8: 15,   # 贷方金额
        9: 8,    # 币别
        10: 8,   # 汇率
        11: 15,  # 原币金额
        12: 8,   # 数量
        13: 10,  # 单价
        14: 10,  # 核算类别
        15: 10,  # 核算代码
        16: 15,  # 核算名称
        17: 10,  # 制单人
        18: 10,  # 审核人
        19: 15,  # 备注
    }
    for col, width in col_widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width

    # === Save ===
    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"kingdee_vouchers_{ts}.xlsx"
        output_path = settings.export_path / filename
    else:
        output_path = Path(output_path)

    wb.save(output_path)
    logger.info(f"Exported {len(entries)} entries ({row - 2} lines) to {output_path}")

    return output_path
