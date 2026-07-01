"""Pydantic schemas for Client."""

from datetime import datetime
from pydantic import BaseModel, Field


class ClientBase(BaseModel):
    name: str = Field(min_length=1, max_length=200, description="企业名称")
    tax_id: str | None = None
    tax_type: str = "small"
    contact_person: str | None = None
    phone: str | None = None
    notes: str | None = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: str | None = None
    tax_id: str | None = None
    tax_type: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class ClientResponse(ClientBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
