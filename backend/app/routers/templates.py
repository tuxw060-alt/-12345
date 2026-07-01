"""Entry template API routes."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import template_service
from app.schemas.journal_entry import EntryResponse

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


class ApplyTemplateRequest(BaseModel):
    template_id: str
    client_id: str
    voucher_date: date
    summary: str | None = None
    amounts: dict[int, float] | None = None


@router.get("")
async def list_templates(
    client_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    templates = await template_service.list_templates(db, client_id)
    return {
        "items": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "summary_template": t.summary_template,
                "voucher_type": t.voucher_type,
                "client_id": t.client_id,
                "lines": [
                    {
                        "line_number": l.line_number,
                        "account_code": l.account_code,
                        "account_name": l.account_name,
                        "direction": l.direction,
                        "amount_source": l.amount_source,
                        "fixed_amount": l.fixed_amount,
                        "summary_detail": l.summary_detail,
                    }
                    for l in t.lines
                ],
            }
            for t in templates
        ],
        "total": len(templates),
    }


@router.post("/apply", response_model=EntryResponse)
async def apply_template(data: ApplyTemplateRequest, db: AsyncSession = Depends(get_db)):
    """Apply a template to create a journal entry."""
    try:
        entry = await template_service.apply_template(
            db, data.template_id, data.client_id,
            data.voucher_date, data.summary, data.amounts,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return EntryResponse.model_validate(entry)
