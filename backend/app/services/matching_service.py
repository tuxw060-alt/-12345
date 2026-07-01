"""Matching rule service — keyword-to-subject matching logic."""

import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.matching_rule import MatchingRule
from app.schemas.matching_rule import MatchingRuleCreate, MatchingRuleUpdate


async def list_rules(
    db: AsyncSession,
    client_id: str | None = None,
    offset: int = 0,
    limit: int = 200,
):
    stmt = select(MatchingRule).where(MatchingRule.is_active == True)

    # Global rules + client-specific rules
    if client_id:
        stmt = stmt.where(
            (MatchingRule.client_id == None) | (MatchingRule.client_id == client_id)
        )
    else:
        stmt = stmt.where(MatchingRule.client_id == None)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(MatchingRule.priority.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return items, total


async def create_rule(db: AsyncSession, data: MatchingRuleCreate) -> MatchingRule:
    import uuid
    rule = MatchingRule(
        id=str(uuid.uuid4()),
        keywords=data.keywords,
        subject_code=data.subject_code,
        subject_name=data.subject_name,
        priority=data.priority,
        client_id=data.client_id,
    )
    db.add(rule)
    await db.flush()
    return rule


async def update_rule(
    db: AsyncSession, rule: MatchingRule, data: MatchingRuleUpdate
) -> MatchingRule:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.flush()
    return rule


async def delete_rule(db: AsyncSession, rule: MatchingRule) -> None:
    rule.is_active = False
    await db.flush()


async def get_rule(db: AsyncSession, rule_id: str) -> MatchingRule | None:
    stmt = select(MatchingRule).where(MatchingRule.id == rule_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def match_text(
    db: AsyncSession, text: str, client_id: str | None = None
) -> dict:
    """Match a text against all active rules. Returns best match (highest priority)."""
    stmt = select(MatchingRule).where(MatchingRule.is_active == True)
    if client_id:
        stmt = stmt.where(
            (MatchingRule.client_id == None) | (MatchingRule.client_id == client_id)
        )
    else:
        stmt = stmt.where(MatchingRule.client_id == None)

    stmt = stmt.order_by(MatchingRule.priority.desc())
    result = await db.execute(stmt)
    rules = result.scalars().all()

    matched_keywords = []
    best_match = None

    for rule in rules:
        keywords = rule.keywords.split("|")
        for kw in keywords:
            if kw.strip() and kw.strip() in text:
                matched_keywords.append(kw.strip())
                if best_match is None or rule.priority > best_match.priority:
                    best_match = rule

    if best_match:
        return {
            "text": text,
            "matched_keywords": matched_keywords,
            "subject_code": best_match.subject_code,
            "subject_name": best_match.subject_name,
            "rule_id": best_match.id,
            "matched": True,
        }
    else:
        return {
            "text": text,
            "matched_keywords": [],
            "subject_code": None,
            "subject_name": None,
            "rule_id": None,
            "matched": False,
        }
