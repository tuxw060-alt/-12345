"""Matching rule API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.matching_rule import (
    MatchingRuleCreate,
    MatchingRuleUpdate,
    MatchingRuleResponse,
    MatchingRuleListResponse,
    MatchingRuleTestRequest,
    MatchingRuleTestResponse,
)
from app.services import matching_service

router = APIRouter(prefix="/api/v1/matching-rules", tags=["matching-rules"])


@router.get("", response_model=MatchingRuleListResponse)
async def list_rules(
    client_id: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    items, total = await matching_service.list_rules(db, client_id, offset, limit)
    return MatchingRuleListResponse(
        items=[MatchingRuleResponse.model_validate(item) for item in items],
        total=total,
    )


@router.post("", response_model=MatchingRuleResponse, status_code=201)
async def create_rule(data: MatchingRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = await matching_service.create_rule(db, data)
    return MatchingRuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=MatchingRuleResponse)
async def update_rule(
    rule_id: str, data: MatchingRuleUpdate, db: AsyncSession = Depends(get_db)
):
    rule = await matching_service.get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    rule = await matching_service.update_rule(db, rule, data)
    return MatchingRuleResponse.model_validate(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    rule = await matching_service.get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    await matching_service.delete_rule(db, rule)
    return None


@router.post("/test", response_model=MatchingRuleTestResponse)
async def test_rule(data: MatchingRuleTestRequest, db: AsyncSession = Depends(get_db)):
    result = await matching_service.match_text(db, data.text, data.client_id)
    return MatchingRuleTestResponse(**result)
