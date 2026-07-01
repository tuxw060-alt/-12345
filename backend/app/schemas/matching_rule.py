"""Pydantic schemas for MatchingRule."""

from datetime import datetime
from pydantic import BaseModel, Field


class MatchingRuleBase(BaseModel):
    keywords: str = Field(..., max_length=500, description="关键词, 用 | 分隔")
    subject_code: str = Field(..., max_length=20, description="目标科目代码")
    subject_name: str | None = None
    priority: int = 0
    client_id: str | None = None


class MatchingRuleCreate(MatchingRuleBase):
    pass


class MatchingRuleUpdate(BaseModel):
    keywords: str | None = None
    subject_code: str | None = None
    subject_name: str | None = None
    priority: int | None = None
    is_active: bool | None = None


class MatchingRuleResponse(MatchingRuleBase):
    id: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchingRuleListResponse(BaseModel):
    items: list[MatchingRuleResponse]
    total: int


class MatchingRuleTestRequest(BaseModel):
    text: str = Field(..., description="测试文本")
    client_id: str | None = None


class MatchingRuleTestResponse(BaseModel):
    text: str
    matched_keywords: list[str]
    subject_code: str | None = None
    subject_name: str | None = None
    rule_id: str | None = None
    matched: bool
