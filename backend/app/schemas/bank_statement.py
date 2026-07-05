"""Pydantic schemas for bank statement recognition."""

from datetime import date, datetime

from pydantic import BaseModel


class BankStatementTransactionResponse(BaseModel):
    id: str
    upload_id: str
    client_id: str
    transaction_date: date | None = None
    summary: str | None = None
    counterparty: str | None = None
    account_number: str | None = None
    income_amount: float | None = None
    expense_amount: float | None = None
    balance: float | None = None
    suggested_subject_code: str | None = None
    suggested_subject_name: str | None = None
    selected_account_code: str | None = None
    selected_account_name: str | None = None
    selected_account_full_name: str | None = None
    selected_parent_account_code: str | None = None
    selected_parent_account_name: str | None = None
    manual_account_override: bool = False
    account_selection_source: str = "auto"
    document_type_id: str | None = None
    document_name: str | None = None
    settlement_method: str | None = None
    business_type: str | None = None
    selected_template_id: str | None = None
    recommended_template_id: str | None = None
    template_match_reason: str | None = None
    subject_reason: str | None = None
    confidence: float | None = None
    status: str
    error_msg: str | None = None
    entry_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BankStatementUploadResponse(BaseModel):
    id: str
    client_id: str
    filename: str
    status: str
    error_msg: str | None = None
    file_type: str | None = None
    processing_mode: str | None = None
    use_ocr: bool = False
    use_ai: bool = False
    processing_display: str | None = None
    processing_description: str | None = None
    total_rows: int | None = None
    valid_rows: int | None = None
    error_rows: int | None = None
    created_at: datetime
    transactions: list[BankStatementTransactionResponse] = []

    model_config = {"from_attributes": True}


class BankStatementUploadResult(BaseModel):
    upload: BankStatementUploadResponse
    entry_ids: list[str] = []


class BankStatementListResponse(BaseModel):
    items: list[BankStatementUploadResponse]
    total: int
