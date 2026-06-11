"""Seed hiring-focused specialty categories for Prozlab."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from app.database.session import SessionLocal
from app.modules.onboarding.constants import HIRING_SPECIALTIES
from app.modules.auth.models.user import User  # noqa: F401 — register mapper for ProzProfile.user
from app.modules.proz.models.proz import ProzProfile, Specialty  # noqa: F401

try:
    from app.modules.tasks.models.task import TaskAssignment, TaskNotification  # noqa: F401
except ImportError:
    pass


def seed_specialties() -> None:
    db = SessionLocal()
    try:
        created = 0
        for name, description in HIRING_SPECIALTIES:
            existing = db.query(Specialty).filter(Specialty.name == name).first()
            if existing:
                existing.description = description
                continue
            db.add(Specialty(name=name, description=description))
            created += 1
        db.commit()
        print(f"Seeded {created} hiring specialties ({len(HIRING_SPECIALTIES)} total defined).")
    finally:
        db.close()


if __name__ == "__main__":
    seed_specialties()
