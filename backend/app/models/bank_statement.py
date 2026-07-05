"""Bank statement upload and parsed transaction models."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BankStatementUpload(Base):
    __tablename__ = "bank_statement_uploads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id"), nullable=False, comment="所属客户"
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="pending / done / failed"
    )
    error_msg: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_ai_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    processing_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    use_ocr: Mapped[bool] = mapped_column(Boolean, default=False)
    use_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_display: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processing_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    total_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    transactions = relationship(
        "BankStatementTransaction",
        back_populates="upload",
        cascade="all, delete-orphan",
        order_by="BankStatementTransaction.transaction_date",
    )


class BankStatementTransaction(Base):
    __tablename__ = "bank_statement_transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    upload_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("bank_statement_uploads.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id"), nullable=False, comment="所属客户"
    )
    transaction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    counterparty: Mapped[str | None] = mapped_column(String(200), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    income_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    expense_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    balance: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    suggested_subject_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    suggested_subject_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    selected_account_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    selected_account_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    selected_account_full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    selected_parent_account_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    selected_parent_account_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    manual_account_override: Mapped[bool] = mapped_column(Boolean, default=False)
    account_selection_source: Mapped[str] = mapped_column(String(30), default="auto")
    document_type_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    document_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    settlement_method: Mapped[str | None] = mapped_column(String(40), nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    selected_template_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recommended_template_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    template_match_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    subject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="recognized", comment="recognized / failed"
    )
    error_msg: Mapped[str | None] = mapped_column(String(500), nullable=True)
    entry_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    upload = relationship("BankStatementUpload", back_populates="transactions")
