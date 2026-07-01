"""Pydantic schemas for JournalEntry and JournalEntryLine."""

from datetime import date, datetime
from pydantic import BaseModel, Field


class EntryLineBase(BaseModel):
    line_number: int = Field(..., ge=1, description="分录行号")
    account_code: str = Field(..., max_length=20, description="科目代码")
    account_name: str = Field(..., max_length=100, description="科目名称")
    direction: str = Field(..., description="debit(借) 或 credit(贷)")
    amount: float = Field(..., gt=0, description="金额")
    summary_detail: str | None = None


class EntryLineCreate(EntryLineBase):
    pass


class EntryLineResponse(EntryLineBase):
    id: str
    entry_id: str

    model_config = {"from_attributes": True}


class EntryBase(BaseModel):
    voucher_date: date = Field(..., description="凭证日期")
    voucher_type: str = Field("记", description="凭证字")
    voucher_number: str | None = None
    summary: str = Field(..., max_length=500, description="摘要")


class EntryCreate(EntryBase):
    client_id: str
    source_invoice_id: str | None = None
    lines: list[EntryLineCreate] = Field(..., min_length=2, description="至少2行分录")


class EntryUpdate(BaseModel):
    voucher_date: date | None = None
    voucher_type: str | None = None
    voucher_number: str | None = None
    summary: str | None = None
    lines: list[EntryLineCreate] | None = None


class EntryResponse(EntryBase):
    id: str
    client_id: str
    source_invoice_id: str | None = None
    status: str
    lines: list[EntryLineResponse]
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class EntryListResponse(BaseModel):
    items: list[EntryResponse]
    total: int


class EntryGenerateRequest(BaseModel):
    """Request to auto-generate a journal entry from an invoice."""
    invoice_id: str
    client_id: str
    voucher_date: date | None = None
    voucher_type: str = "记"
    summary: str | None = None


class EntryGenerateResponse(BaseModel):
    entry: EntryCreate
    suggested: bool = True
    note: str | None = None
