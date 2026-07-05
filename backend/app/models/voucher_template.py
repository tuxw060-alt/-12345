"""DocumentType (单据类别), VoucherTemplate (分录模板), VoucherTemplateLine (模板分录行) models.

Implements the configurable voucher template system:
  上传发票/银行流水 → 识别票据类型 → 识别业务类型 → 匹配分录模板 → 生成凭证草稿
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentType(Base):
    """单据类别 — 销售发票/采购发票/费用票据/银行票据等"""
    __tablename__ = "document_types"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    company_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="所属公司(NULL=全局)"
    )
    code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, comment="编码, e.g. 1001"
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="单据类别: 销售发票/采购发票/费用票据/银行票据"
    )
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="单据名称: 销售增值税发票等"
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否系统预置(预置不可删除,只能停用)"
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())


class VoucherTemplate(Base):
    """票据分录模板 — 定义某类单据在某种业务类型下的标准分录"""
    __tablename__ = "voucher_templates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    company_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="所属公司(NULL=全局)"
    )
    document_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True
    )
    document_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="单据名称(冗余,方便查询)"
    )
    settlement_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default="往来结算",
        comment="结算方式: 往来结算/现金/银行/未结算/其他"
    )
    business_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="业务类型: 销售收入/采购商品/福利费等"
    )
    summary_template: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="摘要模板, 支持{counterpartyName}等变量"
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, comment="优先级, 越大越优先")
    created_from: Mapped[str] = mapped_column(
        String(20), default="system", comment="来源: system/manual/copy"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    lines = relationship(
        "VoucherTemplateLine", back_populates="template",
        cascade="all, delete-orphan", order_by="VoucherTemplateLine.line_no"
    )
    document_type = relationship("DocumentType")


class VoucherTemplateLine(Base):
    """模板分录行 — 一个模板可有多条借贷分录"""
    __tablename__ = "voucher_template_lines"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("voucher_templates.id", ondelete="CASCADE"), nullable=False
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="分录行号")
    debit_credit: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="借贷方向: debit(借) / credit(贷)"
    )
    account_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="科目代码")
    account_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="科目名称")
    account_full_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="科目全称"
    )
    parent_account_code: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="上级科目代码(用于子级匹配范围)"
    )
    amount_source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="totalAmount",
        comment="金额来源: totalAmount/amount/taxAmount/incomeAmount/expenseAmount/balance/manual/zero"
    )
    require_sub_account: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否需要匹配往来明细科目"
    )
    sub_account_match_mode: Mapped[str] = mapped_column(
        String(20), default="none",
        comment="明细匹配方式: none/customer/supplier/counterparty/legacy_sub_account/bank_account"
    )
    allow_manual_edit: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="生成凭证后是否允许手动修改此科目"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now())

    template = relationship("VoucherTemplate", back_populates="lines")
