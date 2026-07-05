"""Document type and voucher template configuration APIs."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.document_voucher import (
    DocumentTypeCreate,
    DocumentTypeResponse,
    DocumentTypeUpdate,
    TemplatePreviewRequest,
    TemplateRecommendation,
    VoucherTemplateCreate,
    VoucherTemplateResponse,
    VoucherTemplateUpdate,
)
from app.services import document_voucher_service as service

router = APIRouter(prefix="/api/v1/document-vouchers", tags=["document-vouchers"])


@router.get("/document-types")
async def list_document_types(
    company_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_document_types(db, company_id)
    return {"items": [DocumentTypeResponse.model_validate(item) for item in items], "total": total}


@router.post("/document-types", response_model=DocumentTypeResponse, status_code=201)
async def create_document_type(data: DocumentTypeCreate, db: AsyncSession = Depends(get_db)):
    try:
        item = await service.create_document_type(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentTypeResponse.model_validate(item)


@router.put("/document-types/{document_type_id}", response_model=DocumentTypeResponse)
async def update_document_type(
    document_type_id: str,
    data: DocumentTypeUpdate,
    db: AsyncSession = Depends(get_db),
):
    item = await service.get_document_type(db, document_type_id)
    if not item:
        raise HTTPException(status_code=404, detail="票据类型不存在")
    try:
        item = await service.update_document_type(db, item, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentTypeResponse.model_validate(item)


@router.delete("/document-types/{document_type_id}", status_code=204)
async def delete_document_type(document_type_id: str, db: AsyncSession = Depends(get_db)):
    item = await service.get_document_type(db, document_type_id)
    if not item:
        raise HTTPException(status_code=404, detail="票据类型不存在")
    try:
        await service.delete_document_type(db, item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return None


@router.post("/document-types/restore-defaults")
async def restore_document_type_defaults(db: AsyncSession = Depends(get_db)):
    await service.restore_default_document_types(db)
    return {"ok": True}


@router.get("/templates")
async def list_templates(
    company_id: str | None = Query(None),
    document_type_id: str | None = Query(None),
    enabled_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_templates(
        db,
        company_id=company_id,
        document_type_id=document_type_id,
        enabled_only=enabled_only,
    )
    return {"items": [VoucherTemplateResponse.model_validate(item) for item in items], "total": total}


@router.post("/templates", response_model=VoucherTemplateResponse, status_code=201)
async def create_template(data: VoucherTemplateCreate, db: AsyncSession = Depends(get_db)):
    try:
        item = await service.create_template(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return VoucherTemplateResponse.model_validate(item)


@router.get("/templates/{template_id}", response_model=VoucherTemplateResponse)
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    item = await service.get_template(db, template_id)
    if not item:
        raise HTTPException(status_code=404, detail="分录模板不存在")
    return VoucherTemplateResponse.model_validate(item)


@router.put("/templates/{template_id}", response_model=VoucherTemplateResponse)
async def update_template(
    template_id: str,
    data: VoucherTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    item = await service.get_template(db, template_id)
    if not item:
        raise HTTPException(status_code=404, detail="分录模板不存在")
    try:
        item = await service.update_template(db, item, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return VoucherTemplateResponse.model_validate(item)


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(template_id: str, db: AsyncSession = Depends(get_db)):
    item = await service.get_template(db, template_id)
    if not item:
        raise HTTPException(status_code=404, detail="分录模板不存在")
    await service.delete_template(db, item)
    return None


@router.post("/templates/{template_id}/copy", response_model=VoucherTemplateResponse)
async def copy_template(template_id: str, db: AsyncSession = Depends(get_db)):
    item = await service.get_template(db, template_id)
    if not item:
        raise HTTPException(status_code=404, detail="分录模板不存在")
    copied = await service.copy_template(db, item)
    return VoucherTemplateResponse.model_validate(copied)


@router.post("/recommend-template", response_model=TemplateRecommendation)
async def recommend_template(data: TemplatePreviewRequest, db: AsyncSession = Depends(get_db)):
    return await service.recommend_template(db, data)
