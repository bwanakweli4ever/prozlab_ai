from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.auth.models.user import User
from app.modules.onboarding.constants import EXPERIENCE_LEVEL_MAP, ONBOARDING_STEPS
from app.modules.onboarding.models.onboarding import OnboardingProgress
from app.modules.proz.models.proz import ProzProfile, ProzSpecialty, Specialty


class OnboardingService:
    TOTAL_STEPS = len(ONBOARDING_STEPS)

    def get_or_create(self, db: Session, user: User) -> OnboardingProgress:
        progress = (
            db.query(OnboardingProgress)
            .filter(OnboardingProgress.user_id == user.id)
            .first()
        )
        if progress:
            return progress

        progress = OnboardingProgress(
            user_id=user.id,
            current_step=1,
            completed_steps=[],
            step_data={},
            is_complete=False,
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
        return progress

    def get_status(self, db: Session, user: User) -> OnboardingProgress:
        return self.get_or_create(db, user)

    def save_step(self, db: Session, user: User, step: str, data: Dict[str, Any]) -> OnboardingProgress:
        if step not in ONBOARDING_STEPS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid step. Must be one of: {', '.join(ONBOARDING_STEPS)}",
            )

        progress = self.get_or_create(db, user)
        step_index = ONBOARDING_STEPS.index(step) + 1

        merged_data = dict(progress.step_data or {})
        merged_data[step] = data
        progress.step_data = merged_data

        completed: List[str] = list(progress.completed_steps or [])
        if step not in completed:
            completed.append(step)
        progress.completed_steps = completed

        if step_index >= progress.current_step:
            progress.current_step = min(step_index + 1, self.TOTAL_STEPS)

        db.commit()
        db.refresh(progress)
        return progress

    def _sync_specialties(self, db: Session, profile: ProzProfile, skills: List[str]) -> None:
        db.query(ProzSpecialty).filter(ProzSpecialty.proz_id == profile.id).delete()

        for skill_name in skills:
            specialty = db.query(Specialty).filter(Specialty.name == skill_name).first()
            if not specialty:
                specialty = Specialty(name=skill_name, description=f"{skill_name} professional")
                db.add(specialty)
                db.flush()

            db.add(ProzSpecialty(proz_id=profile.id, specialty_id=specialty.id))

    def complete(self, db: Session, user: User) -> ProzProfile:
        progress = self.get_or_create(db, user)
        data = progress.step_data or {}

        expertise = data.get("expertise", {})
        experience = data.get("experience", {})
        preferences = data.get("preferences", {})
        portfolio = data.get("portfolio", {})
        profile_step = data.get("profile", {})

        skills: List[str] = expertise.get("skills", [])
        experience_level: Optional[str] = experience.get("experience_level")
        work_types: List[str] = preferences.get("work_types", [])
        portfolio_links: List[str] = portfolio.get("links", [])
        if portfolio.get("link") and portfolio["link"] not in portfolio_links:
            portfolio_links.append(portfolio["link"])

        profile = db.query(ProzProfile).filter(ProzProfile.user_id == user.id).first()
        if not profile:
            profile = db.query(ProzProfile).filter(ProzProfile.email == user.email).first()

        if not profile:
            profile = ProzProfile(
                user_id=user.id,
                first_name=user.first_name or profile_step.get("first_name", ""),
                last_name=user.last_name or profile_step.get("last_name", ""),
                email=user.email,
            )
            db.add(profile)
        else:
            profile.user_id = user.id

        profile.first_name = profile_step.get("first_name") or user.first_name or profile.first_name
        profile.last_name = profile_step.get("last_name") or user.last_name or profile.last_name
        profile.phone_number = profile_step.get("phone_number") or profile.phone_number

        if experience_level:
            profile.experience_level = experience_level
            profile.years_experience = EXPERIENCE_LEVEL_MAP.get(experience_level, profile.years_experience)

        if work_types:
            profile.work_types = work_types
            profile.availability = work_types[0]

        if skills:
            profile.skills = skills
            profile.education = ", ".join(skills)

        if portfolio_links:
            profile.portfolio_links = portfolio_links
            profile.website = portfolio_links[0]

        profile.skill_verification_status = data.get("skills_verification", {}).get(
            "status", "pending"
        )
        profile.onboarding_completed = True

        if skills:
            db.flush()
            self._sync_specialties(db, profile, skills)

        progress.is_complete = True
        progress.current_step = self.TOTAL_STEPS
        if "profile" not in (progress.completed_steps or []):
            progress.completed_steps = list(progress.completed_steps or []) + ["profile"]

        db.commit()
        db.refresh(profile)
        db.refresh(progress)
        return profile
