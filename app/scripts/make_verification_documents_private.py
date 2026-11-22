"""Move identity documents out of the public uploads folder and point evidence links at the private endpoint.

Run once from the backend folder (safe to re-run):
    ./venv/bin/python -m app.scripts.make_verification_documents_private
"""
import shutil
from pathlib import Path

from sqlalchemy.orm.attributes import flag_modified

import app.main  # noqa: F401  (registers every model with SQLAlchemy)
from app.config.database import SessionLocal
from app.config.settings import settings
from app.modules.proz.models.proz import ProzProfile
from app.services.file_service import (
    LEGACY_VERIFICATION_URL_PREFIX,
    PRIVATE_VERIFICATION_DIR,
    VERIFICATION_DOCUMENT_URL_PREFIX,
)


def move_files() -> int:
    public_dir = Path(settings.UPLOAD_DIR) / "verification_documents"
    PRIVATE_VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    moved = 0
    if public_dir.is_dir():
        for item in public_dir.iterdir():
            if item.is_file():
                target = PRIVATE_VERIFICATION_DIR / item.name
                if not target.exists():
                    shutil.move(str(item), str(target))
                    target.chmod(0o640)
                    moved += 1
                else:
                    item.unlink()
        try:
            public_dir.rmdir()
        except OSError:
            pass
    return moved


def rewrite_links() -> int:
    db = SessionLocal()
    changed = 0
    try:
        for profile in db.query(ProzProfile).all():
            items = profile.verification_evidences
            if not isinstance(items, list):
                continue
            touched = False
            new_items = []
            for item in items:
                url = item.get("url") if isinstance(item, dict) else None
                if isinstance(url, str) and LEGACY_VERIFICATION_URL_PREFIX in url:
                    name = url.split(LEGACY_VERIFICATION_URL_PREFIX, 1)[1]
                    item = {**item, "url": f"{VERIFICATION_DOCUMENT_URL_PREFIX}{name}"}
                    touched = True
                new_items.append(item)
            if touched:
                profile.verification_evidences = new_items
                flag_modified(profile, "verification_evidences")
                changed += 1
        db.commit()
    finally:
        db.close()
    return changed


if __name__ == "__main__":
    print(f"Moved {move_files()} document(s) to {PRIVATE_VERIFICATION_DIR}")
    print(f"Updated links on {rewrite_links()} profile(s)")
