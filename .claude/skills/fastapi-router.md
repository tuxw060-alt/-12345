---
name: fastapi-router
description: 创建 FastAPI 路由端点的模板和规范。当用户在 backend/app/routers/ 下新增或修改 API 端点时自动加载。
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
---

# FastAPI 路由开发规范

## 模板

```python
"""路由描述"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.xxx import XxxCreate, XxxResponse, XxxUpdate

router = APIRouter(prefix="/api/v1/xxx", tags=["标签名"])


@router.get("/", response_model=list[XxxResponse])
async def list_xxx(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    """获取列表"""
    ...


@router.post("/", response_model=XxxResponse, status_code=201)
async def create_xxx(
    data: XxxCreate,
    session: AsyncSession = Depends(get_session),
):
    """创建"""
    ...


@router.get("/{item_id}", response_model=XxxResponse)
async def get_xxx(item_id: str, session: AsyncSession = Depends(get_session)):
    """获取单个"""
    ...


@router.put("/{item_id}", response_model=XxxResponse)
async def update_xxx(item_id: str, data: XxxUpdate, session: AsyncSession = Depends(get_session)):
    """更新"""
    ...


@router.delete("/{item_id}", status_code=204)
async def delete_xxx(item_id: str, session: AsyncSession = Depends(get_session)):
    """删除"""
    ...
```

## 规范

1. **URL**: `/api/v1/{资源名复数}`，用连字符分隔单词
2. **路径参数**: 使用数据库实体的 `id` 字段（UUID 字符串）
3. **分页**: 列表接口统一用 `skip` + `limit`
4. **错误处理**: 用 `HTTPException`，给出清晰的中文错误信息
5. **依赖注入**: 数据库 session 通过 `Depends(get_session)` 获取
6. **新建路由后**: 在 `backend/app/main.py` 中 `include_router`
