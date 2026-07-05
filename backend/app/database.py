"""Database engine, session factory, and base model."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.config import settings

# Convert sync SQLite URL to async if needed
db_url = settings.database_url
if "sqlite" in db_url and "aiosqlite" not in db_url:
    db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(db_url, echo=False, future=True)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables. Call at app startup."""
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "sqlite" in db_url:
            await _ensure_sqlite_columns(conn)


async def _ensure_sqlite_columns(conn) -> None:
    """Add columns introduced after initial create_all for local SQLite installs."""
    additions = {
        "journal_entry_lines": {
            "account_full_name": "VARCHAR(200)",
            "parent_account_code": "VARCHAR(20)",
            "parent_account_name": "VARCHAR(100)",
            "auxiliary_type": "VARCHAR(40)",
            "auxiliary_code": "VARCHAR(80)",
            "auxiliary_name": "VARCHAR(200)",
            "counterparty_name": "VARCHAR(200)",
            "counterparty_account": "VARCHAR(80)",
            "source_type": "VARCHAR(40)",
            "source_document_id": "VARCHAR(36)",
            "source_row_id": "VARCHAR(36)",
            "manual_account_override": "BOOLEAN DEFAULT 0",
            "account_selection_source": "VARCHAR(30) DEFAULT 'auto'",
        },
        "bank_statement_transactions": {
            "selected_account_code": "VARCHAR(20)",
            "selected_account_name": "VARCHAR(100)",
            "selected_account_full_name": "VARCHAR(200)",
            "selected_parent_account_code": "VARCHAR(20)",
            "selected_parent_account_name": "VARCHAR(100)",
            "manual_account_override": "BOOLEAN DEFAULT 0",
            "account_selection_source": "VARCHAR(30) DEFAULT 'auto'",
            "document_type_id": "VARCHAR(36)",
            "document_name": "VARCHAR(120)",
            "settlement_method": "VARCHAR(40)",
            "business_type": "VARCHAR(80)",
            "selected_template_id": "VARCHAR(36)",
            "recommended_template_id": "VARCHAR(36)",
            "template_match_reason": "VARCHAR(300)",
        },
        "bank_statement_uploads": {
            "file_type": "VARCHAR(20)",
            "processing_mode": "VARCHAR(40)",
            "use_ocr": "BOOLEAN DEFAULT 0",
            "use_ai": "BOOLEAN DEFAULT 0",
            "processing_display": "VARCHAR(100)",
            "processing_description": "VARCHAR(500)",
            "total_rows": "INTEGER",
            "valid_rows": "INTEGER",
            "error_rows": "INTEGER",
        },
        "account_subjects": {
            "parent_account_name": "VARCHAR(100)",
            "created_from": "VARCHAR(40)",
            "updated_at": "DATETIME",
        },
    }
    for table, columns in additions.items():
        rows = (await conn.execute(text(f"PRAGMA table_info({table})"))).fetchall()
        existing = {row[1] for row in rows}
        for column, ddl in columns.items():
            if column not in existing:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
