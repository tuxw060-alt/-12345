"""Client CRUD API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.client import (
    ClientCreate,
    ClientUpdate,
    ClientResponse,
    ClientListResponse,
)
from app.services import client_service

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])


@router.get("", response_model=ClientListResponse)
async def list_clients(
    is_active: bool | None = Query(True),
    search: str | None = Query(None, description="搜索企业名称或税号"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    items, total = await client_service.list_clients(
        db, is_active=is_active, search=search, offset=offset, limit=limit
    )
    return ClientListResponse(
        items=[ClientResponse.model_validate(item) for item in items],
        total=total,
    )


@router.post("", response_model=ClientResponse, status_code=201)
async def create_client(data: ClientCreate, db: AsyncSession = Depends(get_db)):
    client = await client_service.create_client(db, data)
    return ClientResponse.model_validate(client)


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: str, db: AsyncSession = Depends(get_db)):
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="客户不存在")
    return ClientResponse.model_validate(client)


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str, data: ClientUpdate, db: AsyncSession = Depends(get_db)
):
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="客户不存在")
    client = await client_service.update_client(db, client, data)
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}", status_code=204)
async def delete_client(client_id: str, db: AsyncSession = Depends(get_db)):
    client = await client_service.get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="客户不存在")
    await client_service.delete_client(db, client)
    return None
