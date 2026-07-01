"""Client business logic."""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate


async def list_clients(
    db: AsyncSession,
    is_active: bool | None = True,
    search: str | None = None,
    offset: int = 0,
    limit: int = 100,
):
    stmt = select(Client)
    if is_active is not None:
        stmt = stmt.where(Client.is_active == is_active)
    if search:
        stmt = stmt.where(
            (Client.name.contains(search)) | (Client.tax_id.contains(search))
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(Client.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return items, total


async def get_client(db: AsyncSession, client_id: str) -> Client | None:
    stmt = select(Client).where(Client.id == client_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_client(db: AsyncSession, data: ClientCreate) -> Client:
    client = Client(
        id=str(uuid.uuid4()),
        name=data.name,
        tax_id=data.tax_id,
        tax_type=data.tax_type,
        contact_person=data.contact_person,
        phone=data.phone,
        notes=data.notes,
    )
    db.add(client)
    await db.flush()
    return client


async def update_client(
    db: AsyncSession, client: Client, data: ClientUpdate
) -> Client:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    await db.flush()
    return client


async def delete_client(db: AsyncSession, client: Client) -> None:
    """Soft-delete: mark as inactive."""
    client.is_active = False
    await db.flush()
