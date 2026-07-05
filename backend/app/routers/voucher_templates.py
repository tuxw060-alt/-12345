"""DocumentType + VoucherTemplate API routes."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.voucher_template import (
    DocumentTypeCreate, DocumentTypeUpdate, DocumentTypeResponse, DocumentTypeListResponse,
    VoucherTemplateCreate, VoucherTemplateUpdate,
    VoucherTemplateResponse, VoucherTemplateListResponse,
    GenerateDraftRequest, GenerateDraftResponse,
    MatchTemplatesRequest, MatchTemplatesResponse,
    AmountData,
)
from app.services import voucher_template_engine as engine
from app.services.entry_service import create_entry

router = APIRouter(prefix="/api/v1", tags=["voucher-templates"])


# ═══════════════════════════════════════════════════════════════
# Document Types
# ═══════════════════════════════════════════════════════════════

@router.get("/document-types", response_model=DocumentTypeListResponse)
async def list_document_types(
    enabled_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    items = await engine.list_document_types(db, enabled_only=enabled_only)
    return DocumentTypeListResponse(
        items=[DocumentTypeResponse.model_validate(dt) for dt in items],
        total=len(items),
    )


@router.post("/document-types", response_model=DocumentTypeResponse, status_code=201)
async def create_document_type(data: DocumentTypeCreate, db: AsyncSession = Depends(get_db)):
    # Check duplicate code
    existing = await engine.get_document_type_by_code(db, data.code)
    if existing:
        raise HTTPException(status_code=400, detail=f"编码 {data.code} 已存在")
    dt = await engine.create_document_type(db, data)
    return DocumentTypeResponse.model_validate(dt)


@router.put("/document-types/{dt_id}", response_model=DocumentTypeResponse)
async def update_document_type(
    dt_id: str, data: DocumentTypeUpdate, db: AsyncSession = Depends(get_db)
):
    dt = await engine.get_document_type(db, dt_id)
    if not dt:
        raise HTTPException(status_code=404, detail="单据类别不存在")
    # Check code uniqueness if changing
    if data.code and data.code != dt.code:
        existing = await engine.get_document_type_by_code(db, data.code)
        if existing:
            raise HTTPException(status_code=400, detail=f"编码 {data.code} 已存在")
    dt = await engine.update_document_type(db, dt, data)
    return DocumentTypeResponse.model_validate(dt)


@router.delete("/document-types/{dt_id}", status_code=204)
async def delete_document_type(dt_id: str, db: AsyncSession = Depends(get_db)):
    dt = await engine.get_document_type(db, dt_id)
    if not dt:
        raise HTTPException(status_code=404, detail="单据类别不存在")
    if dt.is_system:
        raise HTTPException(status_code=400, detail="系统预置单据不能删除，只能停用")
    try:
        await engine.delete_document_type(db, dt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return None


@router.post("/document-types/restore-presets", response_model=DocumentTypeListResponse)
async def restore_preset_document_types(db: AsyncSession = Depends(get_db)):
    """恢复预置单据类型：只补齐缺失的预置单据，不覆盖用户自定义"""
    restored = await engine.restore_preset_document_types(db)
    all_items = await engine.list_document_types(db)
    return DocumentTypeListResponse(
        items=[DocumentTypeResponse.model_validate(dt) for dt in all_items],
        total=len(all_items),
    )


# ═══════════════════════════════════════════════════════════════
# Voucher Templates
# ═══════════════════════════════════════════════════════════════

@router.get("/voucher-templates", response_model=VoucherTemplateListResponse)
async def list_voucher_templates(
    enabled_only: bool = Query(False),
    document_type_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    templates = await engine.list_templates(db, enabled_only=enabled_only)
    if document_type_id:
        templates = [t for t in templates if t.document_type_id == document_type_id]
    return VoucherTemplateListResponse(
        items=[VoucherTemplateResponse.model_validate(t) for t in templates],
        total=len(templates),
    )


@router.get("/voucher-templates/{tpl_id}", response_model=VoucherTemplateResponse)
async def get_voucher_template(tpl_id: str, db: AsyncSession = Depends(get_db)):
    tpl = await engine.get_template(db, tpl_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="分录模板不存在")
    return VoucherTemplateResponse.model_validate(tpl)


@router.post("/voucher-templates", response_model=VoucherTemplateResponse, status_code=201)
async def create_voucher_template(data: VoucherTemplateCreate, db: AsyncSession = Depends(get_db)):
    lines_data = [ld.model_dump() for ld in data.lines]
    tpl = await engine.create_template(
        db,
        document_name=data.document_name,
        settlement_method=data.settlement_method,
        business_type=data.business_type,
        summary_template=data.summary_template,
        lines_data=lines_data,
        document_type_id=data.document_type_id,
        company_id=data.company_id,
        priority=data.priority,
    )
    # Re-fetch for relationships
    tpl = await engine.get_template(db, tpl.id)
    return VoucherTemplateResponse.model_validate(tpl)


@router.put("/voucher-templates/{tpl_id}", response_model=VoucherTemplateResponse)
async def update_voucher_template(
    tpl_id: str, data: VoucherTemplateUpdate, db: AsyncSession = Depends(get_db)
):
    tpl = await engine.get_template(db, tpl_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="分录模板不存在")
    update_data = data.model_dump(exclude_unset=True)
    if "lines" in update_data and update_data["lines"]:
        update_data["lines"] = [ld if isinstance(ld, dict) else ld.model_dump()
                                for ld in update_data["lines"]]
    tpl = await engine.update_template(db, tpl, update_data)
    tpl = await engine.get_template(db, tpl.id)
    return VoucherTemplateResponse.model_validate(tpl)


@router.delete("/voucher-templates/{tpl_id}", status_code=204)
async def delete_voucher_template(tpl_id: str, db: AsyncSession = Depends(get_db)):
    tpl = await engine.get_template(db, tpl_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="分录模板不存在")
    await engine.delete_template(db, tpl)
    return None


@router.post("/voucher-templates/{tpl_id}/copy", response_model=VoucherTemplateResponse, status_code=201)
async def copy_voucher_template(tpl_id: str, db: AsyncSession = Depends(get_db)):
    tpl = await engine.get_template(db, tpl_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="分录模板不存在")
    new_tpl = await engine.copy_template(db, tpl)
    new_tpl = await engine.get_template(db, new_tpl.id)
    return VoucherTemplateResponse.model_validate(new_tpl)


@router.put("/voucher-templates/{tpl_id}/toggle", response_model=VoucherTemplateResponse)
async def toggle_voucher_template(tpl_id: str, db: AsyncSession = Depends(get_db)):
    tpl = await engine.get_template(db, tpl_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="分录模板不存在")
    tpl = await engine.toggle_template(db, tpl)
    return VoucherTemplateResponse.model_validate(tpl)


# ═══════════════════════════════════════════════════════════════
# Matching & Generation
# ═══════════════════════════════════════════════════════════════

@router.post("/voucher-templates/match", response_model=MatchTemplatesResponse)
async def match_templates_endpoint(
    data: MatchTemplatesRequest, db: AsyncSession = Depends(get_db)
):
    """根据单据类型/结算方式/业务类型匹配分录模板"""
    # Try to identify business type from search text
    biz_type = data.business_type
    if not biz_type and data.search_text:
        biz_type, _ = engine.identify_business_type(data.search_text)

    matched = await engine.match_templates(
        db,
        document_type_id=data.document_type_id,
        settlement_method=data.settlement_method,
        business_type=biz_type,
    )

    return MatchTemplatesResponse(
        matched_templates=[VoucherTemplateResponse.model_validate(t) for t in matched],
        suggested_document_type_id=data.document_type_id,
        suggested_business_type=biz_type,
        suggested_settlement_method=data.settlement_method,
    )


@router.post("/voucher-templates/generate-draft", response_model=GenerateDraftResponse)
async def generate_draft(
    data: GenerateDraftRequest, db: AsyncSession = Depends(get_db)
):
    """根据模板+金额数据生成凭证草稿预览"""
    tpl = await engine.get_template(db, data.template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="分录模板不存在")

    voucher_date = None
    if data.voucher_date:
        try:
            voucher_date = date.fromisoformat(data.voucher_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式无效，请使用 YYYY-MM-DD")

    draft = await engine.generate_draft_from_template(
        db, tpl, data.amounts, data.client_id,
        voucher_date=voucher_date,
        summary_vars=data.summary_vars,
        counterparty_name=data.counterparty_name,
        source_invoice_id=data.source_invoice_id,
    )

    # If no errors, create the actual entry
    if not draft.errors:
        entry_data = await engine.create_draft_entry(
            db, tpl, data.amounts, data.client_id,
            voucher_date=voucher_date,
            summary_vars=data.summary_vars,
            counterparty_name=data.counterparty_name,
            source_invoice_id=data.source_invoice_id,
        )
        entry = await create_entry(db, entry_data)
        draft.entry_id = entry.id

    return draft
