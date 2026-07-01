"""Financial report API routes."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.services import report_service, client_service

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


class TrialBalanceResponse(BaseModel):
    client_name: str
    date_range: str
    items: list[dict]
    totals: dict


class IncomeStatementResponse(BaseModel):
    client_name: str
    date_range: str
    revenue: list[dict]
    cost: list[dict]
    expense: list[dict]
    total_revenue: float
    total_cost: float
    gross_profit: float
    total_expense: float
    operating_profit: float
    net_profit: float


@router.get("/trial-balance")
async def trial_balance(
    client_id: str = Query(..., description="客户ID"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Generate 科目余额表 for a client."""
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="客户不存在")

    items, totals = await report_service.get_trial_balance(
        db, client_id, date_from, date_to
    )

    date_range = ""
    if date_from or date_to:
        date_range = f"{date_from or '...'} ~ {date_to or '...'}"

    return TrialBalanceResponse(
        client_name=client.name,
        date_range=date_range or "全部期间",
        items=items,
        totals=totals,
    )


@router.get("/income-statement")
async def income_statement(
    client_id: str = Query(..., description="客户ID"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Generate 利润表 for a client."""
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="客户不存在")

    data = await report_service.get_income_statement(db, client_id, date_from, date_to)

    date_range = ""
    if date_from or date_to:
        date_range = f"{date_from or '...'} ~ {date_to or '...'}"

    return IncomeStatementResponse(
        client_name=client.name,
        date_range=date_range or "全部期间",
        **data,
    )


@router.get("/trial-balance/excel")
async def export_trial_balance_excel(
    client_id: str = Query(..., description="客户ID"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Download 科目余额表 as Excel."""
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="客户不存在")

    items, totals = await report_service.get_trial_balance(
        db, client_id, date_from, date_to
    )

    date_range = ""
    if date_from or date_to:
        date_range = f"{date_from or '...'} ~ {date_to or '...'}"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"科目余额表_{client.name}_{ts}.xlsx"
    filepath = settings.export_path / filename

    report_service.export_trial_balance_to_excel(
        items, totals, str(filepath), client.name, date_range
    )

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/income-statement/excel")
async def export_income_statement_excel(
    client_id: str = Query(..., description="客户ID"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Download 利润表 as Excel."""
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="客户不存在")

    data = await report_service.get_income_statement(db, client_id, date_from, date_to)

    date_range = ""
    if date_from or date_to:
        date_range = f"{date_from or '...'} ~ {date_to or '...'}"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"利润表_{client.name}_{ts}.xlsx"
    filepath = settings.export_path / filename

    report_service.export_income_statement_to_excel(
        data, str(filepath), client.name, date_range
    )

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
