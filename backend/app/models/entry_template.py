"""EntryTemplate (凭证模板) — save recurring journal entries as reusable templates.

Common monthly entries like rent, salary, social insurance, depreciation
can be saved once and applied with one click each month.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EntryTemplate(Base):
    """A reusable journal entry template."""
    __tablename__ = "entry_templates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id"), nullable=True,
        comment="NULL=全局模板, 有值=该客户专属"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="模板名称")
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    voucher_type: Mapped[str] = mapped_column(String(10), default="记")
    summary_template: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="摘要模板, 支持{month}等变量"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    lines = relationship(
        "EntryTemplateLine", back_populates="template",
        cascade="all, delete-orphan", order_by="EntryTemplateLine.line_number"
    )


class EntryTemplateLine(Base):
    """One line in a reusable entry template."""
    __tablename__ = "entry_template_lines"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("entry_templates.id", ondelete="CASCADE"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    account_code: Mapped[str] = mapped_column(String(20), nullable=False)
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False, comment="debit/credit")
    amount_source: Mapped[str] = mapped_column(
        String(20), default="fixed", comment="fixed=固定金额 / manual=手动输入"
    )
    fixed_amount: Mapped[float | None] = mapped_column(None, comment="固定金额(amount_source=fixed时)")
    summary_detail: Mapped[str | None] = mapped_column(String(200), nullable=True)

    template = relationship("EntryTemplate", back_populates="lines")
