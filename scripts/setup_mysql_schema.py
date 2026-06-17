#!/usr/bin/env python3
"""Create MySQL schema from SQLAlchemy models and stamp Alembic head."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect, text

from app.config.database import engine
from app.database.base_class import Base

# Import all models so metadata is complete
from app.modules.auth.models.user import User  # noqa: F401
from app.modules.auth.models.otp import OTPVerification  # noqa: F401
from app.modules.auth.models.password_reset import PasswordResetToken  # noqa: F401
from app.modules.onboarding.models.onboarding import OnboardingProgress  # noqa: F401
from app.modules.proz.models.proz import (  # noqa: F401
    ProzProfile,
    ProzSpecialty,
    Review,
    Specialty,
)
from app.modules.tasks.models.task import (  # noqa: F401
    ServiceRequest,
    TaskAssignment,
    TaskNotification,
)


def main() -> int:
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if not tables:
        print("Creating MySQL tables from models...")
        Base.metadata.create_all(bind=engine)
    else:
        print(f"MySQL already has {len(tables)} tables; skipping create_all.")

    with engine.connect() as conn:
        has_alembic = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = 'alembic_version'"
            )
        ).scalar()

    if not has_alembic:
        print("Stamping Alembic head...")
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config(str(ROOT / "alembic.ini"))
        command.stamp(alembic_cfg, "head")
    else:
        print("Alembic version table already exists.")

    print("MySQL schema setup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
