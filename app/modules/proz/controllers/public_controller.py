# app/modules/proz/controllers/public_controller.py
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import math

from app.database.session import get_db
from app.modules.proz.models.proz import ProzProfile, Specialty, ProzSpecialty, Review
from app.modules.proz.schemas.public import (
    PublicProzProfileResponse,
    PublicProzProfileCard,
    PublicProzProfileWithReviews,
    PublicReviewResponse,
    ProfileSearchRequest,
    ProfileSearchResponse,
    FeaturedProfilesResponse,
    ProfileCategoriesResponse,
    ProfileStatsResponse,
    VerificationStatusInfo,
    VerificationStatsResponse
)

router = APIRouter()


@router.get("/profiles", response_model=ProfileSearchResponse)
async def search_public_profiles(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(12, ge=1, le=50, description="Items per page"),
    query: Optional[str] = Query(None, description="Search query"),
    location: Optional[str] = Query(None, description="Filter by location"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    max_hourly_rate: Optional[float] = Query(None, ge=0, description="Maximum hourly rate"),
    min_experience: Optional[int] = Query(None, ge=0, description="Minimum years of experience"),
    availability: Optional[str] = Query(None, description="Availability status"),
    is_featured: Optional[bool] = Query(None, description="Featured profiles only"),
    verification_status: Optional[str] = Query("verified", description="Verification status: verified, pending, rejected, all"),
    show_unverified: Optional[bool] = Query(False, description="Include unverified profiles"),
    sort_by: str = Query("rating", description="Sort by: rating, experience, hourly_rate, created_at, verification_status"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Search and filter public Proz profiles with verification status.
    """
    # Build base query
    query_obj = db.query(ProzProfile)
    
    # Handle verification status filtering
    if verification_status and verification_status.lower() != "all":
        if verification_status.lower() == "verified":
            query_obj = query_obj.filter(ProzProfile.verification_status == "verified")
        elif verification_status.lower() == "pending":
            query_obj = query_obj.filter(ProzProfile.verification_status == "pending")
        elif verification_status.lower() == "rejected":
            query_obj = query_obj.filter(ProzProfile.verification_status == "rejected")
    elif not show_unverified:
        # Default: only show verified profiles unless explicitly requested
        query_obj = query_obj.filter(ProzProfile.verification_status == "verified")
    
    # Apply search filters
    if query:
        search_filter = or_(
            ProzProfile.first_name.ilike(f"%{query}%"),
            ProzProfile.last_name.ilike(f"%{query}%"),
            ProzProfile.bio.ilike(f"%{query}%"),
            ProzProfile.location.ilike(f"%{query}%")
        )
        query_obj = query_obj.filter(search_filter)
    
    if location:
        query_obj = query_obj.filter(ProzProfile.location.ilike(f"%{location}%"))
    
    if specialty:
        query_obj = query_obj.join(ProzSpecialty).join(Specialty).filter(
            Specialty.name.ilike(f"%{specialty}%")
        )
    
    if min_rating is not None:
        query_obj = query_obj.filter(ProzProfile.rating >= min_rating)
    
    if max_hourly_rate is not None:
        query_obj = query_obj.filter(ProzProfile.hourly_rate <= max_hourly_rate)
    
    if min_experience is not None:
        query_obj = query_obj.filter(ProzProfile.years_experience >= min_experience)
    
    if availability:
        query_obj = query_obj.filter(ProzProfile.availability == availability)
    
    if is_featured is not None:
        query_obj = query_obj.filter(ProzProfile.is_featured == is_featured)
    
    # Apply sorting
    if sort_by == "verification_status":
        # Custom sorting for verification status (verified first, then pending, then rejected)
        query_obj = query_obj.order_by(
            func.case(
                (ProzProfile.verification_status == "verified", 1),
                (ProzProfile.verification_status == "pending", 2),
                (ProzProfile.verification_status == "rejected", 3),
                else_=4
            ).asc() if sort_order.lower() == "asc" else func.case(
                (ProzProfile.verification_status == "verified", 1),
                (ProzProfile.verification_status == "pending", 2),
                (ProzProfile.verification_status == "rejected", 3),
                else_=4
            ).desc()
        )
    else:
        sort_column = getattr(ProzProfile, sort_by, ProzProfile.rating)
        if sort_order.lower() == "desc":
            query_obj = query_obj.order_by(sort_column.desc())
        else:
            query_obj = query_obj.order_by(sort_column.asc())
    
    # Get total count
    total_count = query_obj.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    profiles = query_obj.offset(offset).limit(page_size).all()
    
    # Get specialties for each profile
    profile_cards = []
    for profile in profiles:
        specialties = db.query(Specialty.name).join(ProzSpecialty).filter(
            ProzSpecialty.proz_id == profile.id
        ).all()
        
        profile_data = PublicProzProfileCard.model_validate(profile)
        profile_data.specialties = [s.name for s in specialties]
        profile_cards.append(profile_data)
    
    # Calculate pagination info
    total_pages = math.ceil(total_count / page_size)
    
    # Build filters object
    filters_applied = ProfileSearchRequest(
        query=query,
        location=location,
        specialty=specialty,
        min_rating=min_rating,
        max_hourly_rate=max_hourly_rate,
        min_experience=min_experience,
        availability=availability,
        is_featured=is_featured,
        verification_status=verification_status,
        show_unverified=show_unverified
    )
    
    return ProfileSearchResponse(
        profiles=profile_cards,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        filters_applied=filters_applied
    )


@router.get("/profiles/{profile_id}", response_model=PublicProzProfileWithReviews)
async def get_public_profile(
    profile_id: str,
    include_unverified: bool = Query(False, description="Include unverified profiles"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get detailed public profile by ID with verification status consideration.
    """
    # Build query based on verification preferences
    if include_unverified:
        profile = db.query(ProzProfile).filter(ProzProfile.id == profile_id).first()
    else:
        profile = db.query(ProzProfile).filter(
            and_(
                ProzProfile.id == profile_id,
                ProzProfile.verification_status == "verified"
            )
        ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found or not verified"
        )
    
    # Get specialties
    specialties = db.query(Specialty.name).join(ProzSpecialty).filter(
        ProzSpecialty.proz_id == profile.id
    ).all()
    
    # Get approved reviews (only for verified profiles)
    reviews = []
    if profile.verification_status == "verified":
        reviews = db.query(Review).filter(
            and_(
                Review.proz_id == profile.id,
                Review.is_approved == True
            )
        ).order_by(Review.created_at.desc()).limit(10).all()
    
    # Build response
    profile_data = PublicProzProfileWithReviews.model_validate(profile)
    profile_data.specialties = [s.name for s in specialties]
    profile_data.reviews = [PublicReviewResponse.model_validate(r) for r in reviews]
    
    return profile_data


@router.get("/featured", response_model=FeaturedProfilesResponse)
async def get_featured_profiles(
    limit: int = Query(6, ge=1, le=20, description="Number of featured profiles"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get featured profiles for homepage display.
    """
    featured_profiles = db.query(ProzProfile).filter(
        and_(
            ProzProfile.is_featured == True,
            ProzProfile.verification_status == "verified"
        )
    ).order_by(ProzProfile.rating.desc()).limit(limit).all()
    
    # Get specialties for each profile
    profile_cards = []
    for profile in featured_profiles:
        specialties = db.query(Specialty.name).join(ProzSpecialty).filter(
            ProzSpecialty.proz_id == profile.id
        ).all()
        
        profile_data = PublicProzProfileCard.model_validate(profile)
        profile_data.specialties = [s.name for s in specialties]
        profile_cards.append(profile_data)
    
    total_featured = db.query(ProzProfile).filter(
        and_(
            ProzProfile.is_featured == True,
            ProzProfile.verification_status == "verified"
        )
    ).count()
    
    return FeaturedProfilesResponse(
        featured_profiles=profile_cards,
        total_featured=total_featured
    )


@router.get("/categories", response_model=ProfileCategoriesResponse)
async def get_profile_categories(
    db: Session = Depends(get_db)
) -> Any:
    """
    Get available categories and filters for the frontend.
    """
    # Get all specialties
    specialties = db.query(Specialty.name).distinct().all()
    specialty_names = [s.name for s in specialties]
    
    # Get all locations from verified profiles
    locations = db.query(ProzProfile.location).filter(
        and_(
            ProzProfile.location.isnot(None),
            ProzProfile.verification_status == "verified"
        )
    ).distinct().all()
    location_names = [l.location for l in locations if l.location]
    
    # Availability options
    availability_options = ["full-time", "part-time", "contract", "unavailable"]
    
    # Experience ranges
    experience_ranges = [
        {"label": "0-2 years", "min": 0, "max": 2},
        {"label": "3-5 years", "min": 3, "max": 5},
        {"label": "6-10 years", "min": 6, "max": 10},
        {"label": "10+ years", "min": 10, "max": None}
    ]
    
    # Rating ranges
    rating_ranges = [
        {"label": "4+ stars", "min": 4.0, "max": None},
        {"label": "3+ stars", "min": 3.0, "max": None},
        {"label": "2+ stars", "min": 2.0, "max": None}
    ]
    
    return ProfileCategoriesResponse(
        specialties=sorted(specialty_names),
        locations=sorted(location_names),
        availability_options=availability_options,
        experience_ranges=experience_ranges,
        rating_ranges=rating_ranges
    )


@router.get("/stats", response_model=ProfileStatsResponse)
async def get_profile_stats(
    db: Session = Depends(get_db)
) -> Any:
    """
    Get public statistics for the platform including verification stats.
    """
    # Total profiles
    total_profiles = db.query(ProzProfile).count()
    
    # Verified profiles
    verified_profiles = db.query(ProzProfile).filter(
        ProzProfile.verification_status == "verified"
    ).count()
    
    # Pending profiles  
    pending_profiles = db.query(ProzProfile).filter(
        ProzProfile.verification_status == "pending"
    ).count()
    
    # Rejected profiles
    rejected_profiles = db.query(ProzProfile).filter(
        ProzProfile.verification_status == "rejected"
    ).count()
    
    # Featured profiles
    featured_profiles = db.query(ProzProfile).filter(
        and_(
            ProzProfile.is_featured == True,
            ProzProfile.verification_status == "verified"
        )
    ).count()
    
    # Specialties count
    specialties_count = db.query(Specialty).count()
    
    # Average rating (only verified profiles)
    avg_rating_result = db.query(func.avg(ProzProfile.rating)).filter(
        ProzProfile.verification_status == "verified"
    ).scalar()
    average_rating = round(float(avg_rating_result or 0), 2)
    
    # Unique locations count (only verified profiles)
    locations_count = db.query(ProzProfile.location).filter(
        and_(
            ProzProfile.location.isnot(None),
            ProzProfile.verification_status == "verified"
        )
    ).distinct().count()
    
    return ProfileStatsResponse(
        total_profiles=total_profiles,
        verified_profiles=verified_profiles,
        pending_profiles=pending_profiles,
        rejected_profiles=rejected_profiles,
        featured_profiles=featured_profiles,
        specialties_count=specialties_count,
        average_rating=average_rating,
        locations_count=locations_count
    )


@router.get("/verification-info", response_model=VerificationStatsResponse)
async def get_verification_info(
    db: Session = Depends(get_db)
) -> Any:
    """
    Get verification status information and statistics.
    """
    # Define verification status information
    verification_statuses = [
        VerificationStatusInfo(
            status="verified",
            label="Verified",
            description="Profile has been verified by our team",
            badge_color="green",
            show_publicly=True
        ),
        VerificationStatusInfo(
            status="pending",
            label="Under Review",
            description="Profile is currently being reviewed",
            badge_color="yellow",
            show_publicly=False
        ),
        VerificationStatusInfo(
            status="rejected",
            label="Not Verified",
            description="Profile did not meet verification requirements",
            badge_color="red",
            show_publicly=False
        )
    ]
    
    # Get stats by verification status
    stats_by_status = {}
    for status_info in verification_statuses:
        count = db.query(ProzProfile).filter(
            ProzProfile.verification_status == status_info.status
        ).count()
        stats_by_status[status_info.status] = count
    
    return VerificationStatsResponse(
        verification_statuses=verification_statuses,
        stats_by_status=stats_by_status
    )


@router.get("/verified-only", response_model=ProfileSearchResponse)
async def get_verified_profiles_only(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    sort_by: str = Query("rating", description="Sort by: rating, experience, hourly_rate, created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get only verified profiles (simplified endpoint for public website).
    """
    return await search_public_profiles(
        page=page,
        page_size=page_size,
        verification_status="verified",
        sort_by=sort_by,
        sort_order=sort_order,
        db=db
    )


@router.get("/pending-verification", response_model=ProfileSearchResponse)
async def get_pending_verification_profiles(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get profiles pending verification (for admin/review purposes).
    """
    return await search_public_profiles(
        page=page,
        page_size=page_size,
        verification_status="pending",
        show_unverified=True,
        sort_by=sort_by,
        sort_order=sort_order,
        db=db
    )


@router.get("/profiles/{profile_id}/reviews", response_model=List[PublicReviewResponse])
async def get_profile_reviews(
    profile_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get paginated reviews for a specific profile.
    """
    # Verify profile exists and is verified
    profile = db.query(ProzProfile).filter(
        and_(
            ProzProfile.id == profile_id,
            ProzProfile.verification_status == "verified"
        )
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found or not verified"
        )
    
    # Get approved reviews with pagination
    offset = (page - 1) * page_size
    reviews = db.query(Review).filter(
        and_(
            Review.proz_id == profile_id,
            Review.is_approved == True
        )
    ).order_by(Review.created_at.desc()).offset(offset).limit(page_size).all()
    
    return [PublicReviewResponse.model_validate(review) for review in reviews]


@router.get("/search-suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2, description="Search query"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get search suggestions for autocomplete.
    """
    suggestions = {
        "profiles": [],
        "specialties": [],
        "locations": []
    }
    
    # Profile name suggestions
    profiles = db.query(ProzProfile.first_name, ProzProfile.last_name).filter(
        and_(
            or_(
                ProzProfile.first_name.ilike(f"%{q}%"),
                ProzProfile.last_name.ilike(f"%{q}%")
            ),
            ProzProfile.verification_status == "verified"
        )
    ).limit(5).all()
    
    suggestions["profiles"] = [f"{p.first_name} {p.last_name}" for p in profiles]
    
    # Specialty suggestions
    specialties = db.query(Specialty.name).filter(
        Specialty.name.ilike(f"%{q}%")
    ).limit(5).all()
    
    suggestions["specialties"] = [s.name for s in specialties]
    
    # Location suggestions
    locations = db.query(ProzProfile.location).filter(
        and_(
            ProzProfile.location.ilike(f"%{q}%"),
            ProzProfile.verification_status == "verified"
        )
    ).distinct().limit(5).all()
    
    suggestions["locations"] = [l.location for l in locations if l.location]
    
    return suggestions