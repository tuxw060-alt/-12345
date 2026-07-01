"""
Journal entry generation from invoice data.

Automatically generates proper double-entry bookkeeping entries
based on invoice type, client tax status, and AI-suggested subjects.
"""

from datetime import date
from loguru import logger

from app.models.invoice import Invoice
from app.models.client import Client
from app.schemas.journal_entry import EntryCreate, EntryLineCreate


def generate_entry_from_invoice(
    invoice: Invoice,
    client: Client | None = None,
    voucher_date: date | None = None,
    voucher_type: str = "记",
    summary: str | None = None,
) -> EntryCreate:
    """
    Generate journal entry lines from an invoice.

    Logic:
    - For expense invoices (most common case):
        Debit:  suggested_subject_code        (amount)
        Debit:  2221.01.01 (进项税额)           (tax_amount) [only if 专票 + 一般纳税人]
        Credit: 1002 (银行存款) / 2202 (应付账款) (total_amount)

    - For revenue invoices:
        Debit:  1002 (银行存款) / 1122 (应收账款) (total_amount)
        Credit: 5001 (主营业务收入)              (amount)
        Credit: 2221.01.02 (销项税额)            (tax_amount)
    """
    is_general = client and client.tax_type == "general"
    is_special_invoice = invoice.invoice_type and "专用发票" in invoice.invoice_type

    # Determine if this is a deductible VAT invoice
    can_deduct = is_general and is_special_invoice

    # Amounts
    amount = invoice.amount or 0
    tax_amount = invoice.tax_amount or 0
    total_amount = invoice.total_amount or (amount + tax_amount)

    # Subject code
    subject_code = invoice.suggested_subject_code or "5602.99"  # default: 管理费用-其他
    subject_name = invoice.suggested_subject_name or "管理费用-其他"

    # Build summary
    if not summary:
        vendor = invoice.vendor_name or "对方"
        items = invoice.item_name or "费用"
        summary = f"{vendor} {items}"
        if invoice.invoice_number:
            summary += f" 发票#{invoice.invoice_number}"

    # Determine credit account (default: 银行存款)
    # For most small businesses, we use 银行存款 as the credit side
    credit_account_code = "1002"
    credit_account_name = "银行存款"

    lines: list[EntryLineCreate] = []
    line_num = 1

    # === Debit side ===
    # Main expense subject
    lines.append(EntryLineCreate(
        line_number=line_num,
        account_code=subject_code,
        account_name=subject_name,
        direction="debit",
        amount=round(amount, 2),
        summary_detail=invoice.item_name or "",
    ))
    line_num += 1

    # VAT input tax (if deductible)
    if can_deduct and tax_amount > 0:
        lines.append(EntryLineCreate(
            line_number=line_num,
            account_code="2221.01.01",
            account_name="应交税费-应交增值税(进项税额)",
            direction="debit",
            amount=round(tax_amount, 2),
            summary_detail=f"发票#{invoice.invoice_number} 进项税额",
        ))
        line_num += 1

    # === Credit side ===
    credit_amount = total_amount if can_deduct else (amount + (0 if can_deduct else tax_amount))
    # If not deducting, tax is included in the expense amount already
    # Actually, if not deducting, total = amount + tax, all to expense
    if not can_deduct and tax_amount > 0:
        # Adjust: the expense line already has 'amount', we need to add tax to it
        lines[0].amount = round(amount + tax_amount, 2)
        credit_amount = round(amount + tax_amount, 2)
    else:
        credit_amount = round(total_amount, 2)

    lines.append(EntryLineCreate(
        line_number=line_num,
        account_code=credit_account_code,
        account_name=credit_account_name,
        direction="credit",
        amount=round(credit_amount, 2),
        summary_detail="支付" if voucher_type == "付" else "",
    ))

    # Validate: debit total == credit total
    debit_total = sum(l.amount for l in lines if l.direction == "debit")
    credit_total = sum(l.amount for l in lines if l.direction == "credit")
    diff = round(debit_total - credit_total, 2)
    if abs(diff) > 0.01:
        logger.warning(
            f"Entry unbalanced: debit={debit_total}, credit={credit_total}, diff={diff}"
        )

    return EntryCreate(
        voucher_date=voucher_date or invoice.invoice_date or date.today(),
        voucher_type=voucher_type,
        summary=summary,
        client_id=invoice.client_id or "",
        source_invoice_id=invoice.id,
        lines=lines,
    )
