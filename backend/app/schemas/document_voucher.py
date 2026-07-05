"""Pydantic schemas for document voucher configuration."""

from datetime import datetime

from pydantic import BaseModel, Field


SETTLEMENT_METHODS = {"往来结算", "现金", "银行", "未结算", "其他"}
AMOUNT_SOURCES = {
    "totalAmount",
    "amount",
    "taxAmount",
    "incomeAmount",
    "expenseAmount",
    "balance",
    "manual",
    "zero",
}
DEBIT_CREDITS = {"debit", "credit"}
SUB_ACCOUNT_MATCH_MODES = {
    "none",
    "customer",
    "supplier",
    "counterparty",
    "legacy_sub_account",
    "bank_account",
}


class DocumentTypeBase(BaseModel):
    company_id: str | None = None
    code: str = Field(..., max_length=20)
    category: str = Field(..., max_length=80)
    name: str = Field(..., max_length=120)
    is_enabled: bool = True


class DocumentTypeCreate(DocumentTypeBase):
    pass


class DocumentTypeUpdate(BaseModel):
    code: str | None = Field(None, max_length=20)
    category: str | None = Field(None, max_length=80)
    name: str | None = Field(None, max_length=120)
    is_enabled: bool | None = None


class DocumentTypeResponse(DocumentTypeBase):
    id: str
    is_system: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class TemplateLineBase(BaseModel):
    line_no: int = Field(..., ge=1)
    debit_credit: str
    account_code: str = Field(..., max_length=20)
    account_name: str = Field(..., max_length=120)
    account_full_name: str | None = Field(None, max_length=220)
    parent_account_code: str | None = Field(None, max_length=20)
    amount_source: str
    require_sub_account: bool = False
    sub_account_match_mode: str = "none"
    allow_manual_edit: bool = True


class TemplateLineCreate(TemplateLineBase):
    pass


class TemplateLineResponse(TemplateLineBase):
    id: str
    template_id: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class VoucherTemplateBase(BaseModel):
    company_id: str | None = None
    document_type_id: str
    document_name: str = Field(..., max_length=120)
    settlement_method: str = Field(..., max_length=40)
    business_type: str = Field(..., max_length=80)
    summary_template: str = Field(..., max_length=300)
    is_enabled: bool = True
    priority: int = 100
    created_from: str = "user"


class VoucherTemplateCreate(VoucherTemplateBase):
    lines: list[TemplateLineCreate] = Field(..., min_length=2)


class VoucherTemplateUpdate(BaseModel):
    document_type_id: str | None = None
    document_name: str | None = Field(None, max_length=120)
    settlement_method: str | None = Field(None, max_length=40)
    business_type: str | None = Field(None, max_length=80)
    summary_template: str | None = Field(None, max_length=300)
    is_enabled: bool | None = None
    priority: int | None = None
    lines: list[TemplateLineCreate] | None = None


class VoucherTemplateResponse(VoucherTemplateBase):
    id: str
    created_at: datetime
    updated_at: datetime | None = None
    lines: list[TemplateLineResponse] = []

    model_config = {"from_attributes": True}


class ListResponse(BaseModel):
    items: list[DocumentTypeResponse] | list[VoucherTemplateResponse]
    total: int


class TemplatePreviewRequest(BaseModel):
    document_type_id: str | None = None
    document_name: str | None = None
    settlement_method: str | None = None
    business_type: str | None = None
    summary: str | None = None
    counterparty_name: str | None = None
    total_amount: float | None = None
    amount: float | None = None
    tax_amount: float | None = None
    income_amount: float | None = None
    expense_amount: float | None = None
    balance: float | None = None
    template_id: str | None = None
    client_id: str | None = None


class TemplateRecommendation(BaseModel):
    template_id: str | None = None
    document_type_id: str | None = None
    document_name: str | None = None
    settlement_method: str | None = None
    business_type: str
    confidence: float
    reason: str | None = None
