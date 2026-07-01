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
    created_at: datetime
    transactions: list[BankStatementTransactionResponse] = []

    model_config = {"from_attributes": True}


class BankStatementUploadResult(BaseModel):
    upload: BankStatementUploadResponse
    entry_ids: list[str] = []


class BankStatementListResponse(BaseModel):
    items: list[BankStatementUploadResponse]
    total: int
