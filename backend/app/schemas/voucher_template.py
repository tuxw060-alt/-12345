"""Pydantic schemas for DocumentType, VoucherTemplate, VoucherTemplateLine."""

from datetime import datetime
from pydantic import BaseModel, Field


# ── DocumentType ──────────────────────────────────────────────

class DocumentTypeBase(BaseModel):
    code: str = Field(..., max_length=20, description="编码")
    category: str = Field(..., max_length=50, description="单据类别")
    name: str = Field(..., max_length=100, description="单据名称")


class DocumentTypeCreate(DocumentTypeBase):
    company_id: str | None = None
    is_system: bool = False
    is_enabled: bool = True


class DocumentTypeUpdate(BaseModel):
    code: str | None = None
    category: str | None = None
    name: str | None = None
    is_enabled: bool | None = None


class DocumentTypeResponse(DocumentTypeBase):
    id: str
    company_id: str | None = None
    is_system: bool
    is_enabled: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocumentTypeListResponse(BaseModel):
    items: list[DocumentTypeResponse]
    total: int


# ── VoucherTemplateLine ───────────────────────────────────────

class VoucherTemplateLineBase(BaseModel):
    line_no: int = Field(..., ge=1, description="分录行号")
    debit_credit: str = Field(..., description="debit(借) / credit(贷)")
    account_code: str = Field(..., max_length=20, description="科目代码")
    account_name: str = Field(..., max_length=100, description="科目名称")
    account_full_name: str | None = None
    parent_account_code: str | None = None
    amount_source: str = Field(
        default="totalAmount",
        description="totalAmount/amount/taxAmount/incomeAmount/expenseAmount/balance/manual/zero"
    )
    require_sub_account: bool = False
    sub_account_match_mode: str = Field(
        default="none",
        description="none/customer/supplier/counterparty/legacy_sub_account/bank_account"
    )
    allow_manual_edit: bool = True


class VoucherTemplateLineCreate(VoucherTemplateLineBase):
    pass


class VoucherTemplateLineUpdate(VoucherTemplateLineBase):
    line_no: int | None = Field(None, ge=1)
    debit_credit: str | None = None
    account_code: str | None = None
    account_name: str | None = None
    amount_source: str | None = None


class VoucherTemplateLineResponse(VoucherTemplateLineBase):
    id: str
    template_id: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── VoucherTemplate ───────────────────────────────────────────

class VoucherTemplateBase(BaseModel):
    document_type_id: str | None = None
    document_name: str = Field(..., max_length=100, description="单据名称")
    settlement_method: str = Field(
        default="往来结算", description="往来结算/现金/银行/未结算/其他"
    )
    business_type: str = Field(..., max_length=50, description="业务类型")
    summary_template: str = Field(
        default="", max_length=300, description="摘要模板, 支持{变量}"
    )


class VoucherTemplateCreate(VoucherTemplateBase):
    company_id: str | None = None
    priority: int = 0
    is_enabled: bool = True
    lines: list[VoucherTemplateLineCreate] = Field(..., min_length=1, description="分录行列表")


class VoucherTemplateUpdate(BaseModel):
    document_type_id: str | None = None
    document_name: str | None = None
    settlement_method: str | None = None
    business_type: str | None = None
    summary_template: str | None = None
    is_enabled: bool | None = None
    priority: int | None = None
    lines: list[VoucherTemplateLineCreate] | None = None


class VoucherTemplateResponse(VoucherTemplateBase):
    id: str
    company_id: str | None = None
    is_enabled: bool
    priority: int
    created_from: str
    lines: list[VoucherTemplateLineResponse] = []
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class VoucherTemplateListResponse(BaseModel):
    items: list[VoucherTemplateResponse]
    total: int


# ── Generate Draft ────────────────────────────────────────────

class AmountData(BaseModel):
    """金额数据，用于模板生成凭证"""
    total_amount: float = 0.0      # 价税合计
    amount: float = 0.0            # 不含税金额
    tax_amount: float = 0.0        # 税额
    income_amount: float = 0.0     # 收入金额(银行流水)
    expense_amount: float = 0.0    # 支出金额(银行流水)
    balance: float = 0.0           # 余额


class GenerateDraftRequest(BaseModel):
    """根据模板生成凭证草稿的请求"""
    template_id: str
    client_id: str
    voucher_date: str | None = None  # YYYY-MM-DD
    amounts: AmountData = Field(default_factory=AmountData)
    summary_vars: dict[str, str] = Field(
        default_factory=dict, description="摘要变量替换, e.g. {counterpartyName: '张三'}"
    )
    counterparty_name: str | None = None  # 对方名称(用于往来明细匹配)
    source_invoice_id: str | None = None
    source_transaction_id: str | None = None


class PreviewLine(BaseModel):
    """生成预览：每行分录的预览信息"""
    line_no: int
    debit_credit: str
    account_code: str
    account_name: str
    amount_source: str
    estimated_amount: float
    require_sub_account: bool
    sub_account_match_mode: str
    matched_sub_code: str | None = None
    matched_sub_name: str | None = None
    is_pending: bool = False  # 匹配不到子级明细时为True
    warning: str | None = None


class GenerateDraftResponse(BaseModel):
    """生成凭证草稿的响应"""
    entry_id: str | None = None
    status: str  # "draft" or "error"
    preview_lines: list[PreviewLine]
    warnings: list[str] = []
    errors: list[str] = []


class MatchTemplatesRequest(BaseModel):
    """匹配模板请求"""
    document_type_id: str | None = None
    settlement_method: str | None = None
    business_type: str | None = None
    search_text: str | None = None  # 用于从文本中识别业务类型


class MatchTemplatesResponse(BaseModel):
    """匹配模板结果"""
    matched_templates: list[VoucherTemplateResponse]
    suggested_document_type_id: str | None = None
    suggested_business_type: str | None = None
    suggested_settlement_method: str | None = None
