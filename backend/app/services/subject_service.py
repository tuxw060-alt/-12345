"""AccountSubject business logic."""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.account_subject import AccountSubject
from app.schemas.account_subject import SubjectCreate, SubjectUpdate


async def list_subjects(
    db: AsyncSession,
    client_id: str | None = None,
    category: str | None = None,
    search: str | None = None,
    leaf_only: bool = False,
    offset: int = 0,
    limit: int = 500,
):
    """List subjects with optional filters."""
    stmt = select(AccountSubject).where(AccountSubject.is_active == True)

    if client_id is not None:
        # Include global subjects (client_id IS NULL) plus client-specific ones
        stmt = stmt.where(
            (AccountSubject.client_id == None) | (AccountSubject.client_id == client_id)
        )

    if category:
        stmt = stmt.where(AccountSubject.category == category)

    if search:
        stmt = stmt.where(
            (AccountSubject.code.contains(search))
            | (AccountSubject.name.contains(search))
            | (AccountSubject.full_name.contains(search))
        )

    if leaf_only:
        stmt = stmt.where(AccountSubject.is_leaf == True)

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Fetch
    stmt = stmt.order_by(AccountSubject.code).offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return items, total


async def get_subject_by_code(db: AsyncSession, code: str) -> AccountSubject | None:
    stmt = select(AccountSubject).where(AccountSubject.code == code)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_subject_by_id(db: AsyncSession, subject_id: str) -> AccountSubject | None:
    stmt = select(AccountSubject).where(AccountSubject.id == subject_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_subject(db: AsyncSession, data: SubjectCreate) -> AccountSubject:
    subject = AccountSubject(
        id=str(uuid.uuid4()),
        client_id=data.client_id,
        code=data.code,
        name=data.name,
        full_name=data.full_name or data.name,
        level=data.level,
        parent_code=data.parent_code,
        category=data.category,
        direction=data.direction,
        is_leaf=data.is_leaf,
    )
    db.add(subject)
    await db.flush()
    return subject


async def update_subject(
    db: AsyncSession, subject: AccountSubject, data: SubjectUpdate
) -> AccountSubject:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(subject, field, value)
    await db.flush()
    return subject


async def build_subject_tree(
    db: AsyncSession, client_id: str | None = None
) -> list[dict]:
    """Build a hierarchical subject tree for frontend display."""
    from app.schemas.account_subject import SubjectTreeNode

    stmt = select(AccountSubject).where(AccountSubject.is_active == True)
    if client_id is not None:
        stmt = stmt.where(
            (AccountSubject.client_id == None) | (AccountSubject.client_id == client_id)
        )
    stmt = stmt.order_by(AccountSubject.code)
    result = await db.execute(stmt)
    subjects = result.scalars().all()

    # Build tree
    node_map: dict[str, dict] = {}
    roots: list[dict] = []

    for s in subjects:
        node = {
            "code": s.code,
            "name": s.name,
            "full_name": s.full_name,
            "level": s.level,
            "direction": s.direction,
            "is_leaf": s.is_leaf,
            "children": [],
        }
        node_map[s.code] = node

        if s.parent_code and s.parent_code in node_map:
            node_map[s.parent_code]["children"].append(node)
        else:
            roots.append(node)

    return roots
