"""Account subject API routes."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.account_subject import (
    SubjectCreate,
    SubjectImportResponse,
    SubjectListResponse,
    SubjectResponse,
    SubjectUpdate,
)
from app.services import subject_service

router = APIRouter(prefix="/api/v1/subjects", tags=["subjects"])


class NextSubAccountCodeResponse(BaseModel):
    parent_code: str
    next_code: str


@router.get("", response_model=SubjectListResponse)
async def list_subjects(
    client_id: str | None = Query(None, description="客户ID；传入时同时返回全局和客户科目"),
    category: str | None = Query(None, description="资产/负债/权益/成本/损益"),
    search: str | None = Query(None, description="搜索科目编码或名称"),
    leaf_only: bool = Query(False, description="仅末级科目"),
    offset: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    items, total = await subject_service.list_subjects(
        db,
        client_id=client_id,
        category=category,
        search=search,
        leaf_only=leaf_only,
        offset=offset,
        limit=limit,
    )
    return SubjectListResponse(
        items=[SubjectResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get("/tree", response_model=list[dict])
async def subject_tree(
    client_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Return subjects as a hierarchical tree."""
    return await subject_service.build_subject_tree(db, client_id=client_id)


@router.post("/import-legacy", response_model=SubjectImportResponse)
async def import_legacy_subjects(
    file: UploadFile = File(...),
    client_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or "legacy-subjects.xls"
    try:
        content = await file.read()
        if not content:
            raise ValueError("上传文件为空")
        return await subject_service.import_legacy_subjects(
            db,
            filename=filename,
            content=content,
            client_id=client_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/next-sub-code", response_model=NextSubAccountCodeResponse)
async def next_sub_account_code(
    parent_code: str = Query(...),
    client_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    items, _ = await subject_service.list_subjects(
        db,
        client_id=client_id,
        leaf_only=True,
        offset=0,
        limit=1000,
    )
    child_codes = [item.code for item in items if item.parent_code == parent_code]
    return NextSubAccountCodeResponse(
        parent_code=parent_code,
        next_code=subject_service.generate_next_sub_account_code(parent_code, child_codes),
    )


@router.get("/{code}", response_model=SubjectResponse)
async def get_subject(code: str, db: AsyncSession = Depends(get_db)):
    subject = await subject_service.get_subject_by_code(db, code)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    return SubjectResponse.model_validate(subject)


@router.post("", response_model=SubjectResponse, status_code=201)
async def create_subject(data: SubjectCreate, db: AsyncSession = Depends(get_db)):
    existing = await subject_service.get_subject_by_code(db, data.code)
    if existing:
        raise HTTPException(status_code=400, detail=f"科目编码 {data.code} 已存在")
    subject = await subject_service.create_subject(db, data)
    return SubjectResponse.model_validate(subject)


@router.put("/{code}", response_model=SubjectResponse)
async def update_subject(
    code: str, data: SubjectUpdate, db: AsyncSession = Depends(get_db)
):
    subject = await subject_service.get_subject_by_code(db, code)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    subject = await subject_service.update_subject(db, subject, data)
    return SubjectResponse.model_validate(subject)


@router.delete("/{code}", status_code=204)
async def delete_subject(code: str, db: AsyncSession = Depends(get_db)):
    subject = await subject_service.get_subject_by_code(db, code)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    subject.is_active = False
    await db.flush()
    return None
