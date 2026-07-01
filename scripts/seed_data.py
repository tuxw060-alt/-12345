"""
Seed script: populates the database with standard accounting subjects and matching rules.

Usage:
    cd backend
    python -m scripts.seed_data
    # or
    python ../scripts/seed_data.py
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import text
from app.database import async_session, engine, Base
from app.models import AccountSubject, MatchingRule


ASSETS_DIR = Path(__file__).resolve().parent.parent / "backend" / "assets" / "subjects"


async def seed_subjects():
    """Load standard subjects from JSON and insert into database."""
    filepath = ASSETS_DIR / "standard_subjects.json"
    if not filepath.exists():
        print(f"✗ Subjects file not found: {filepath}")
        return 0

    data = json.loads(filepath.read_text(encoding="utf-8"))
    subjects = data["subjects"]

    async with async_session() as session:
        # Check if already seeded
        result = await session.execute(text("SELECT COUNT(*) FROM account_subjects"))
        count = result.scalar()
        if count > 0:
            print(f"  Subjects already seeded ({count} records), skipping.")
            return count

        for s in subjects:
            full_name = s.get("full_name") or f"{s['name']}"
            subject = AccountSubject(
                id=str(uuid.uuid4()),
                code=s["code"],
                name=s["name"],
                full_name=full_name,
                level=s["level"],
                parent_code=s.get("parent_code"),
                category=s["category"],
                direction=s["direction"],
                is_leaf=s.get("is_leaf", True),
            )
            session.add(subject)

        await session.commit()
        print(f"  ✓ Seeded {len(subjects)} account subjects.")
        return len(subjects)


async def seed_matching_rules():
    """Load matching rules from JSON and insert into database."""
    filepath = ASSETS_DIR / "matching_rules.json"
    if not filepath.exists():
        print(f"✗ Rules file not found: {filepath}")
        return 0

    data = json.loads(filepath.read_text(encoding="utf-8"))
    rules = data["rules"]

    async with async_session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM matching_rules"))
        count = result.scalar()
        if count > 0:
            print(f"  Matching rules already seeded ({count} records), skipping.")
            return count

        for r in rules:
            rule = MatchingRule(
                id=str(uuid.uuid4()),
                keywords=r["keywords"],
                subject_code=r["subject_code"],
                priority=r.get("priority", 0),
            )
            session.add(rule)

        await session.commit()
        print(f"  ✓ Seeded {len(rules)} matching rules.")
        return len(rules)


async def main():
    print("Seeding database...")

    # Create tables first
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Tables created.")

    await seed_subjects()
    await seed_matching_rules()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
