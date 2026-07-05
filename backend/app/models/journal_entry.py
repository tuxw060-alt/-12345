"""JournalEntry (记账凭证) and JournalEntryLine (分录行) models."""

import uuid
from datetime import date, datetime
from sqlalchemy import Boolean, String, Integer, Date, Numeric, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id"), nullable=False, comment="所属客户"
    )
    source_invoice_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("invoices.id"), nullable=True, comment="来源发票(可空)"
    )

    # Voucher header
    voucher_date: Mapped[date] = mapped_column(Date, nullable=False, comment="凭证日期")
    voucher_type: Mapped[str] = mapped_column(
        String(10), default="记", comment="凭证字: 记/收/付/转"
    )
    voucher_number: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="凭证号")
    summary: Mapped[str] = mapped_column(String(500), nullable=False, comment="摘要")

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="draft", comment="draft / confirmed / exported"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    client = relationship("Client", back_populates="journal_entries")
    lines = relationship(
        "JournalEntryLine", back_populates="entry",
        cascade="all, delete-orphan", order_by="JournalEntryLine.line_number"
    )

    def __repr__(self) -> str:
        return f"<Entry {self.voucher_type}-{self.voucher_number or '?'} {self.voucher_date}>"


class JournalEntryLine(Base):
    __tablename__ = "journal_entry_lines"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False, comment="分录行号 1/2/3")
    account_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="科目代码")
    account_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="科目名称")
    direction: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="借/debit 或 贷/credit"
    )
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, comment="金额")
    summary_detail: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="分行业务说明"
    )

    account_full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    parent_account_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    parent_account_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    auxiliary_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    auxiliary_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    auxiliary_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    counterparty_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    counterparty_account: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_row_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    manual_account_override: Mapped[bool] = mapped_column(Boolean, default=False)
    account_selection_source: Mapped[str] = mapped_column(String(30), default="auto")

    # Relationships
    entry = relationship("JournalEntry", back_populates="lines")

    def __repr__(self) -> str:
        return f"<EntryLine {self.direction} {self.account_code} {self.amount}>"
