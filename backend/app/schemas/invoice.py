"""Pydantic schemas for Invoice."""

from datetime import date, datetime
from pydantic import BaseModel, Field


class InvoiceResponse(BaseModel):
    id: str
    client_id: str | None = None
    image_filename: str
    invoice_type: str | None = None
    invoice_code: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    total_amount: float | None = None
    amount: float | None = None
    tax_amount: float | None = None
    vendor_name: str | None = None
    vendor_tax_id: str | None = None
    buyer_name: str | None = None
    buyer_tax_id: str | None = None
    item_name: str | None = None
    remarks: str | None = None
    suggested_subject_code: str | None = None
    suggested_subject_name: str | None = None
    subject_confidence: float | None = None
    ocr_status: str
    ocr_confidence: float | None = None
    ocr_error_msg: str | None = None
    raw_ai_response: dict | None = None
    human_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceUpdate(BaseModel):
    """Fields the user can manually correct after AI extraction."""
    invoice_type: str | None = None
    invoice_code: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    total_amount: float | None = None
    amount: float | None = None
    tax_amount: float | None = None
    vendor_name: str | None = None
    vendor_tax_id: str | None = None
    buyer_name: str | None = None
    buyer_tax_id: str | None = None
    item_name: str | None = None
    remarks: str | None = None
    suggested_subject_code: str | None = None
    suggested_subject_name: str | None = None
    client_id: str | None = None
    human_verified: bool | None = None


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
