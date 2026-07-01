"""Pydantic schemas for AccountSubject."""

from datetime import datetime
from pydantic import BaseModel, Field


class SubjectBase(BaseModel):
    code: str = Field(..., max_length=20, description="科目代码")
    name: str = Field(..., max_length=100, description="科目名称")
    full_name: str | None = None
    level: int = 1
    parent_code: str | None = None
    category: str = Field(..., description="类别: 资产/负债/权益/成本/损益")
    direction: str = "debit"
    is_leaf: bool = True


class SubjectCreate(SubjectBase):
    client_id: str | None = None


class SubjectUpdate(BaseModel):
    name: str | None = None
    full_name: str | None = None
    is_leaf: bool | None = None
    is_active: bool | None = None
    direction: str | None = None


class SubjectResponse(SubjectBase):
    id: str
    client_id: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SubjectTreeNode(BaseModel):
    """Tree node for hierarchical subject display."""
    code: str
    name: str
    full_name: str | None = None
    level: int
    direction: str
    is_leaf: bool
    children: list["SubjectTreeNode"] = []


class SubjectListResponse(BaseModel):
    items: list[SubjectResponse]
    total: int
