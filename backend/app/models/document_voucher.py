"""Configurable document types and document voucher templates."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentType(Base):
    __tablename__ = "document_types"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_document_type_company_code"),
        UniqueConstraint("company_id", "name", name="uq_document_type_company_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("clients.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    templates = relationship("DocumentVoucherTemplate", back_populates="document_type")


class DocumentVoucherTemplate(Base):
    __tablename__ = "document_voucher_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("clients.id"), nullable=True)
    document_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_types.id"), nullable=False)
    document_name: Mapped[str] = mapped_column(String(120), nullable=False)
    settlement_method: Mapped[str] = mapped_column(String(40), nullable=False)
    business_type: Mapped[str] = mapped_column(String(80), nullable=False)
    summary_template: Mapped[str] = mapped_column(String(300), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    created_from: Mapped[str] = mapped_column(String(40), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    document_type = relationship("DocumentType", back_populates="templates")
    lines = relationship(
        "DocumentVoucherTemplateLine",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="DocumentVoucherTemplateLine.line_no",
    )


class DocumentVoucherTemplateLine(Base):
    __tablename__ = "document_voucher_template_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_voucher_templates.id", ondelete="CASCADE"), nullable=False
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    debit_credit: Mapped[str] = mapped_column(String(10), nullable=False)
    account_code: Mapped[str] = mapped_column(String(20), nullable=False)
    account_name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_full_name: Mapped[str | None] = mapped_column(String(220), nullable=True)
    parent_account_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amount_source: Mapped[str] = mapped_column(String(40), nullable=False)
    require_sub_account: Mapped[bool] = mapped_column(Boolean, default=False)
    sub_account_match_mode: Mapped[str] = mapped_column(String(40), default="none")
    allow_manual_edit: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    template = relationship("DocumentVoucherTemplate", back_populates="lines")
