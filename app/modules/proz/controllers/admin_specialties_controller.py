from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.models.user import User
from app.modules.auth.services.auth_service import get_current_superuser
from app.modules.proz.models.proz import ProzSpecialty, Specialty
from app.modules.proz.repositories.proz_repository import SpecialtyRepository
from app.modules.proz.schemas.specialty_admin import (
    SpecialtyAdminResponse,
    SpecialtyCreate,
    SpecialtyUpdate,
)

router = APIRouter()
specialty_repo = SpecialtyRepository()


def _to_admin_response(db: Session, specialty: Specialty) -> SpecialtyAdminResponse:
    count = db.query(ProzSpecialty).filter(ProzSpecialty.specialty_id == specialty.id).count()
    return SpecialtyAdminResponse(
        id=str(specialty.id),
        name=specialty.name,
        description=specialty.description,
        profiles_count=count,
        created_at=specialty.created_at,
        updated_at=specialty.updated_at,
    )


@router.get("/specialties", response_model=List[SpecialtyAdminResponse])
async def list_specialties_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    rows = db.query(Specialty).order_by(Specialty.name.asc()).all()
    return [_to_admin_response(db, row) for row in rows]


@router.post("/specialties/seed", response_model=dict)
async def seed_specialties_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    from app.modules.onboarding.constants import HIRING_SPECIALTIES

    created = 0
    updated = 0
    for name, description in HIRING_SPECIALTIES:
        existing = specialty_repo.get_by_name(db, name)
        if existing:
            if description and existing.description != description:
                existing.description = description
                updated += 1
            continue
        specialty_repo.create(db, name, description)
        created += 1
    return {
        "created": created,
        "updated": updated,
        "total_defined": len(HIRING_SPECIALTIES),
        "total_in_db": db.query(Specialty).count(),
    }


@router.post("/specialties", response_model=SpecialtyAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_specialty_admin(
    payload: SpecialtyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    existing = specialty_repo.get_by_name(db, payload.name.strip())
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Specialty already exists")
    specialty = specialty_repo.create(db, payload.name.strip(), payload.description)
    return _to_admin_response(db, specialty)


@router.put("/specialties/{specialty_id}", response_model=SpecialtyAdminResponse)
async def update_specialty_admin(
    specialty_id: str,
    payload: SpecialtyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    specialty = specialty_repo.get_by_id(db, specialty_id)
    if not specialty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialty not found")

    if payload.name and payload.name.strip() != specialty.name:
        conflict = specialty_repo.get_by_name(db, payload.name.strip())
        if conflict and str(conflict.id) != specialty_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Specialty name already in use")

    updated = specialty_repo.update(
        db,
        specialty_id,
        name=payload.name.strip() if payload.name else None,
        description=payload.description,
    )
    return _to_admin_response(db, updated)


@router.delete("/specialties/{specialty_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_specialty_admin(
    specialty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> None:
    specialty = specialty_repo.get_by_id(db, specialty_id)
    if not specialty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialty not found")

    in_use = db.query(ProzSpecialty).filter(ProzSpecialty.specialty_id == specialty.id).count()
    if in_use > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete specialty used by {in_use} profile(s)",
        )

    specialty_repo.delete(db, specialty_id)
