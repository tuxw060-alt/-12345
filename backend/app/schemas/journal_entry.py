"""Pydantic schemas for JournalEntry and JournalEntryLine."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


def _money(value: Any) -> float:
    """Parse a monetary value, returning absolute non-negative float."""
    try:
        parsed = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(abs(parsed) + 0.0000001, 2)


class EntryLineBase(BaseModel):
    line_number: int = Field(..., ge=1, description="分录行号")
    account_code: str = Field(..., max_length=20, description="科目编码")
    account_name: str = Field(..., max_length=100, description="科目名称")
    direction: str = Field(..., description="debit or credit")
    debitAmount: float = Field(0, ge=0, description="借方金额")
    creditAmount: float = Field(0, ge=0, description="贷方金额")
    summary_detail: str | None = None
    account_full_name: str | None = None
    parent_account_code: str | None = None
    parent_account_name: str | None = None
    auxiliary_type: str | None = None
    auxiliary_code: str | None = None
    auxiliary_name: str | None = None
    counterparty_name: str | None = None
    counterparty_account: str | None = None
    source_type: str | None = None
    source_document_id: str | None = None
    source_row_id: str | None = None
    manual_account_override: bool = False
    account_selection_source: str = "auto"

    @model_validator(mode="before")
    @classmethod
    def normalize_amount_fields(cls, data: Any):
        if not isinstance(data, dict):
            direction = getattr(data, "direction", None)
            db_amount = getattr(data, "amount", None)
            existing_debit = getattr(data, "debitAmount", None)
            existing_credit = getattr(data, "creditAmount", None)

            # Prefer existing debitAmount/creditAmount if present
            if existing_debit is not None or existing_credit is not None:
                debit_val = _money(existing_debit)
                credit_val = _money(existing_credit)
            elif db_amount is not None:
                # Derive from legacy amount + direction
                amt = _money(db_amount)
                debit_val = amt if direction == "debit" else 0
                credit_val = amt if direction == "credit" else 0
            else:
                debit_val = 0.0
                credit_val = 0.0

            data = {
                "line_number": getattr(data, "line_number", None),
                "account_code": getattr(data, "account_code", None),
                "account_name": getattr(data, "account_name", None),
                "direction": direction,
                "debitAmount": debit_val,
                "creditAmount": credit_val,
                "summary_detail": getattr(data, "summary_detail", None),
                "account_full_name": getattr(data, "account_full_name", None),
                "parent_account_code": getattr(data, "parent_account_code", None),
                "parent_account_name": getattr(data, "parent_account_name", None),
                "auxiliary_type": getattr(data, "auxiliary_type", None),
                "auxiliary_code": getattr(data, "auxiliary_code", None),
                "auxiliary_name": getattr(data, "auxiliary_name", None),
                "counterparty_name": getattr(data, "counterparty_name", None),
                "counterparty_account": getattr(data, "counterparty_account", None),
                "source_type": getattr(data, "source_type", None),
                "source_document_id": getattr(data, "source_document_id", None),
                "source_row_id": getattr(data, "source_row_id", None),
                "manual_account_override": getattr(data, "manual_account_override", False),
                "account_selection_source": getattr(data, "account_selection_source", "auto"),
                "id": getattr(data, "id", None),
                "entry_id": getattr(data, "entry_id", None),
            }
        else:
            data = dict(data)

        direction = data.get("direction")
        # Preserve both amounts — normalize without zeroing out valid data
        data["debitAmount"] = _money(data.get("debitAmount"))
        data["creditAmount"] = _money(data.get("creditAmount"))
        return data

    @model_validator(mode="after")
    def normalize_direction(self):
        debit = _money(self.debitAmount)
        credit = _money(self.creditAmount)
        if self.direction == "credit":
            self.creditAmount = credit or debit
            self.debitAmount = 0
        else:
            self.debitAmount = debit or credit
            self.creditAmount = 0
        return self


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
    sourceRowIds: list[str] = []
    lines: list[EntryLineCreate] = Field(..., min_length=2, description="至少2行分录")


class EntryUpdate(BaseModel):
    voucher_date: date | None = None
    voucher_type: str | None = None
    voucher_number: str | None = None
    summary: str | None = None
    sourceRowIds: list[str] | None = None
    lines: list[EntryLineCreate] | None = None


class EntryResponse(EntryBase):
    id: str
    client_id: str
    source_invoice_id: str | None = None
    status: str
    confirmedAt: datetime | None = None
    sourceRowIds: list[str] = []
    lines: list[EntryLineResponse]
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def normalize_header_fields(cls, data: Any):
        if isinstance(data, dict):
            data = dict(data)
            if data.get("confirmed_at") is not None and data.get("confirmedAt") is None:
                data["confirmedAt"] = data.get("confirmed_at")
            if data.get("source_row_ids") is not None and not data.get("sourceRowIds"):
                data["sourceRowIds"] = data.get("source_row_ids") or []
            return data
        return {
            "id": getattr(data, "id", None),
            "client_id": getattr(data, "client_id", None),
            "source_invoice_id": getattr(data, "source_invoice_id", None),
            "voucher_date": getattr(data, "voucher_date", None),
            "voucher_type": getattr(data, "voucher_type", None),
            "voucher_number": getattr(data, "voucher_number", None),
            "summary": getattr(data, "summary", None),
            "status": getattr(data, "status", None),
            "confirmedAt": getattr(data, "confirmed_at", None),
            "sourceRowIds": getattr(data, "source_row_ids", None) or [],
            "lines": getattr(data, "lines", []),
            "created_at": getattr(data, "created_at", None),
            "updated_at": getattr(data, "updated_at", None),
        }


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
