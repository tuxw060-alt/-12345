"""Pydantic schemas for account subjects."""

from datetime import datetime

from pydantic import BaseModel, Field


class SubjectBase(BaseModel):
    code: str = Field(..., max_length=20, description="科目编码")
    name: str = Field(..., max_length=100, description="科目名称")
    full_name: str | None = None
    level: int = 1
    parent_code: str | None = None
    parent_account_name: str | None = None
    category: str = Field(..., description="资产/负债/权益/成本/损益")
    direction: str = "debit"
    is_leaf: bool = True


class SubjectCreate(SubjectBase):
    client_id: str | None = None
    created_from: str | None = None


class SubjectUpdate(BaseModel):
    name: str | None = None
    full_name: str | None = None
    parent_account_name: str | None = None
    is_leaf: bool | None = None
    is_active: bool | None = None
    direction: str | None = None


class SubjectResponse(SubjectBase):
    id: str
    client_id: str | None = None
    is_active: bool
    created_from: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class SubjectTreeNode(BaseModel):
    """Tree node for hierarchical subject display."""

    code: str
    name: str
    full_name: str | None = None
    level: int
    parent_code: str | None = None
    parent_account_name: str | None = None
    direction: str
    is_leaf: bool
    children: list["SubjectTreeNode"] = []


class SubjectListResponse(BaseModel):
    items: list[SubjectResponse]
    total: int


class SubjectImportConflict(BaseModel):
    code: str
    name: str
    reason: str
    existing_code: str | None = None
    existing_name: str | None = None


class SubjectImportResponse(BaseModel):
    filename: str
    parent_code: str | None = None
    parent_name: str | None = None
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    conflicts: list[SubjectImportConflict] = []
    warnings: list[str] = []
