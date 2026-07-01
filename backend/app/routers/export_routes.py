"""
Export API routes — generate Kingdee-compatible Excel files
for 金蝶快记帐 "凭证引入" (voucher import).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.services import export_service, entry_service

router = APIRouter(prefix="/api/v1/export", tags=["export"])


class ExportRequest(BaseModel):
    client_id: str | None = Field(None, description="客户ID")
    date_from: date | None = Field(None, description="凭证日期起")
    date_to: date | None = Field(None, description="凭证日期止")
    entry_ids: list[str] | None = Field(None, description="指定导出凭证ID列表")


class ExportPreviewResponse(BaseModel):
    entry_count: int
    line_count: int
    client_name: str | None = None
    date_range: str | None = None
    entries: list[dict]


@router.post("/preview", response_model=ExportPreviewResponse)
async def preview_export(data: ExportRequest, db: AsyncSession = Depends(get_db)):
    """Preview what will be exported without generating a file."""
    if data.entry_ids:
        entries = []
        for eid in data.entry_ids:
            entry = await entry_service.get_entry(db, eid)
            if entry and entry.status in ("confirmed",):
                entries.append(entry)
    else:
        entries = await export_service.get_entries_for_export(
            db,
            client_id=data.client_id,
            date_from=data.date_from,
            date_to=data.date_to,
        )

    if not entries:
        raise HTTPException(status_code=404, detail="没有可导出的凭证（请先确认凭证）")

    line_count = sum(len(e.lines) for e in entries)

    return ExportPreviewResponse(
        entry_count=len(entries),
        line_count=line_count,
        client_name=entries[0].client.name if entries[0].client else None,
        date_range=f"{entries[-1].voucher_date} ~ {entries[0].voucher_date}"
        if len(entries) > 1 else str(entries[0].voucher_date),
        entries=[
            {
                "id": e.id,
                "voucher_date": str(e.voucher_date),
                "voucher_type": e.voucher_type,
                "voucher_number": e.voucher_number,
                "summary": e.summary,
                "line_count": len(e.lines),
            }
            for e in entries
        ],
    )


@router.post("/kingdee")
async def export_kingdee(data: ExportRequest, db: AsyncSession = Depends(get_db)):
    """Generate and download a Kingdee-compatible Excel file."""
    if data.entry_ids:
        entries = []
        for eid in data.entry_ids:
            entry = await entry_service.get_entry(db, eid)
            if entry and entry.status in ("confirmed",):
                entries.append(entry)
    else:
        entries = await export_service.get_entries_for_export(
            db,
            client_id=data.client_id,
            date_from=data.date_from,
            date_to=data.date_to,
        )

    if not entries:
        raise HTTPException(status_code=404, detail="没有可导出的凭证")

    # Generate Excel
    filepath = export_service.generate_kingdee_excel(entries)

    # Mark entries as exported
    for entry in entries:
        entry.status = "exported"
    await db.flush()

    # Return file download
    return FileResponse(
        path=str(filepath),
        filename=filepath.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
