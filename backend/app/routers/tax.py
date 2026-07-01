"""Tax summary API routes."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import tax_service, client_service

router = APIRouter(prefix="/api/v1/tax", tags=["tax"])


@router.get("/summary")
async def tax_summary(
    client_id: str = Query(..., description="客户ID"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get tax liability summary for a client."""
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="客户不存在")
    data = await tax_service.get_tax_summary(db, client_id, date_from, date_to)
    return {"client_name": client.name, **data}
