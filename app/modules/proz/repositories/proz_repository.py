"""
Repository layer for Proz Profile module.
File location: app/modules/proz/repositories/proz_repository.py
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.modules.proz.models.proz import ProzProfile, Specialty, ProzSpecialty, Review, VerificationStatus


class SpecialtyRepository:
    def get_by_id(self, db: Session, specialty_id: str) -> Optional[Specialty]:
        """Get a specialty by ID"""
        return db.query(Specialty).filter(Specialty.id == specialty_id).first()
    
    def get_by_name(self, db: Session, name: str) -> Optional[Specialty]:
        """Get a specialty by name"""
        return db.query(Specialty).filter(Specialty.name == name).first()
    
    def get_all(self, db: Session) -> List[Specialty]:
        """Get all specialties"""
        return db.query(Specialty).all()
    
    def create(self, db: Session, name: str) -> Specialty:
        """Create a new specialty"""
        specialty = Specialty(name=name)
        db.add(specialty)
        db.commit()
        db.refresh(specialty)
        return specialty
    
    def get_or_create(self, db: Session, name: str) -> Specialty:
        """Get a specialty by name or create if it doesn't exist"""
        specialty = self.get_by_name(db, name)
        if not specialty:
            specialty = self.create(db, name)
        return specialty
    
    def update(self, db: Session, specialty_id: str, name: str) -> Optional[Specialty]:
        """Update a specialty name"""
        specialty = self.get_by_id(db, specialty_id)
        if specialty:
            specialty.name = name
            db.commit()
            db.refresh(specialty)
        return specialty
    
    def delete(self, db: Session, specialty_id: str) -> bool:
        """Delete a specialty"""
        specialty = self.get_by_id(db, specialty_id)
        if specialty:
            db.delete(specialty)
            db.commit()
            return True
        return False


class ProzProfileRepository:
    def get_by_id(self, db: Session, profile_id: str) -> Optional[ProzProfile]:
        """Get a profile by ID"""
        return db.query(ProzProfile).filter(ProzProfile.id == profile_id).first()
    
    def get_by_email(self, db: Session, email: str) -> Optional[ProzProfile]:
        """Get a profile by email"""
        return db.query(ProzProfile).filter(ProzProfile.email == email).first()
    
    def get_all(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 10,
        location: Optional[str] = None,
        specialty: Optional[str] = None,
        min_experience: Optional[int] = None,
        max_rate: Optional[float] = None,
        availability: Optional[str] = None,
        verification_status: VerificationStatus = VerificationStatus.VERIFIED
    ) -> Tuple[List[ProzProfile], int]:
        """
        Get all profiles with optional filtering
        Returns a tuple of (profiles, total_count)
        """
        query = db.query(ProzProfile)
        
        # Apply filters
        query = query.filter(ProzProfile.verification_status == verification_status)
        
        if location:
            query = query.filter(ProzProfile.location.ilike(f"%{location}%"))
        
        if specialty:
            query = query.join(ProzProfile.specialties).join(ProzSpecialty.specialty).filter(
                Specialty.name.ilike(f"%{specialty}%")
            )
        
        if min_experience is not None:
            query = query.filter(ProzProfile.years_experience >= min_experience)
        
        if max_rate is not None:
            query = query.filter(ProzProfile.hourly_rate <= max_rate)
        
        if availability:
            query = query.filter(ProzProfile.availability.ilike(f"%{availability}%"))
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        profiles = query.offset(skip).limit(limit).all()
        
        return profiles, total
    
    def get_featured(self, db: Session, limit: int = 10) -> List[ProzProfile]:
        """Get featured profiles"""
        return (
            db.query(ProzProfile)
            .filter(
                ProzProfile.verification_status == VerificationStatus.VERIFIED,
                ProzProfile.is_featured == True
            )
            .limit(limit)
            .all()
        )
    
    def create(self, db: Session, profile_data: Dict[str, Any], specialties: List[Specialty] = None) -> ProzProfile:
        """Create a new profile with optional specialties"""
        # Create profile
        profile = ProzProfile(**profile_data)
        db.add(profile)
        db.flush()
        
        # Add specialties if provided
        if specialties:
            for specialty in specialties:
                proz_specialty = ProzSpecialty(proz_id=profile.id, specialty_id=specialty.id)
                db.add(proz_specialty)
        
        db.commit()
        db.refresh(profile)
        return profile
    
    def update(self, db: Session, profile: ProzProfile, update_data: Dict[str, Any], specialties: List[Specialty] = None) -> ProzProfile:
        """Update a profile with optional specialties"""
        # Update profile fields
        for key, value in update_data.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)
        
        # Update specialties if provided
        if specialties is not None:
            # Remove existing specialties
            db.query(ProzSpecialty).filter(ProzSpecialty.proz_id == profile.id).delete()
            
            # Add new specialties
            for specialty in specialties:
                proz_specialty = ProzSpecialty(proz_id=profile.id, specialty_id=specialty.id)
                db.add(proz_specialty)
        
        db.commit()
        db.refresh(profile)
        return profile
    
    def update_verification_status(self, db: Session, profile: ProzProfile, status: VerificationStatus) -> ProzProfile:
        """Update verification status of a profile"""
        profile.verification_status = status
        db.commit()
        db.refresh(profile)
        return profile
    
    def update_profile_image(self, db: Session, profile: ProzProfile, image_url: str) -> ProzProfile:
        """Update profile image URL"""
        profile.profile_image_url = image_url
        db.commit()
        db.refresh(profile)
        return profile
    
    def set_featured(self, db: Session, profile: ProzProfile, is_featured: bool) -> ProzProfile:
        """Set featured status of a profile"""
        profile.is_featured = is_featured
        db.commit()
        db.refresh(profile)
        return profile
    
    def delete(self, db: Session, profile_id: str) -> bool:
        """Delete a profile and all related data"""
        profile = db.query(ProzProfile).filter(ProzProfile.id == profile_id).first()
        if not profile:
            return False
        
        # Delete related specialties
        db.query(ProzSpecialty).filter(ProzSpecialty.proz_id == profile_id).delete()
        
        # Delete related reviews
        db.query(Review).filter(Review.proz_id == profile_id).delete()
        
        # Delete profile
        db.delete(profile)
        db.commit()
        return True


class ReviewRepository:
    def get_by_id(self, db: Session, review_id: str) -> Optional[Review]:
        """Get a review by ID"""
        return db.query(Review).filter(Review.id == review_id).first()
    
    def get_by_proz_id(self, db: Session, proz_id: str) -> List[Review]:
        """Get all reviews for a profile"""
        return db.query(Review).filter(Review.proz_id == proz_id).all()
    
    def create(self, db: Session, proz_id: str, review_data: Dict[str, Any]) -> Review:
        """Create a new review and update profile rating"""
        # Create review
        review = Review(proz_id=proz_id, **review_data)
        db.add(review)
        db.flush()
        
        # Update profile rating
        self.update_profile_rating(db, proz_id)
        
        db.commit()
        db.refresh(review)
        return review
    
    def update(self, db: Session, review_id: str, update_data: Dict[str, Any]) -> Optional[Review]:
        """Update a review and recalculate profile rating"""
        review = self.get_by_id(db, review_id)
        if not review:
            return None
            
        # Update review fields
        for key, value in update_data.items():
            if hasattr(review, key):
                setattr(review, key, value)
        
        db.flush()
        
        # Update profile rating
        self.update_profile_rating(db, review.proz_id)
        
        db.commit()
        db.refresh(review)
        return review
    
    def delete(self, db: Session, review_id: str) -> bool:
        """Delete a review and recalculate profile rating"""
        review = self.get_by_id(db, review_id)
        if not review:
            return False
            
        proz_id = review.proz_id
        
        # Delete review
        db.delete(review)
        db.flush()
        
        # Update profile rating
        self.update_profile_rating(db, proz_id)
        
        db.commit()
        return True
    
    def update_profile_rating(self, db: Session, proz_id: str) -> None:
        """Recalculate and update profile rating and review count"""
        # Calculate new average rating
        avg_rating = db.query(func.avg(Review.rating)).filter(Review.proz_id == proz_id).scalar() or 0
        review_count = db.query(Review).filter(Review.proz_id == proz_id).count()
        
        # Update profile
        profile = db.query(ProzProfile).filter(ProzProfile.id == proz_id).first()
        if profile:
            profile.rating = float(avg_rating)
            profile.review_count = review_count
            db.commit()