# app/modules/tasks/controllers/task_controller.py
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from datetime import datetime, timedelta
import math

from app.database.session import get_db
from app.modules.auth.services.auth_service import AuthService
from app.modules.auth.models.user import User
from app.modules.proz.models.proz import ProzProfile, Specialty, ProzSpecialty
from app.modules.tasks.models.task import ServiceRequest, TaskAssignment, TaskNotification, TaskStatus, TaskPriority
from app.modules.tasks.schemas.task import (
    ServiceRequestCreate,
    ServiceRequestResponse,
    TaskAssignmentCreate,
    TaskAssignmentResponse,
    ProfessionalTaskResponse,
    TaskResponseUpdate,
    NotificationResponse,
    DashboardStatsResponse,
    AdminTaskStatsResponse,
    TaskSearchFilters
)

router = APIRouter()
auth_service = AuthService()


# ==================== PUBLIC ENDPOINTS ====================

@router.post("/service-requests", response_model=ServiceRequestResponse)
async def create_service_request(
    request: ServiceRequestCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new service request from a company/client.
    """
    service_request = ServiceRequest(**request.model_dump())
    db.add(service_request)
    db.commit()
    db.refresh(service_request)
    
    # Add assignments count
    service_request.assignments_count = 0
    
    return ServiceRequestResponse.model_validate(service_request)


@router.get("/service-requests/{request_id}", response_model=ServiceRequestResponse)
async def get_service_request(
    request_id: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get service request details (public endpoint for clients to check status).
    """
    service_request = db.query(ServiceRequest).filter(
        ServiceRequest.id == request_id
    ).first()
    
    if not service_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found"
        )
    
    # Count assignments
    assignments_count = db.query(TaskAssignment).filter(
        TaskAssignment.service_request_id == request_id
    ).count()
    
    service_request.assignments_count = assignments_count
    
    return ServiceRequestResponse.model_validate(service_request)


# ==================== ADMIN ENDPOINTS ====================

@router.get("/admin/service-requests", response_model=dict)
async def get_service_requests_admin(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_superuser)
) -> Any:
    """
    Get service requests for admin management.
    """
    query_obj = db.query(ServiceRequest)
    
    # Apply filters
    if status:
        query_obj = query_obj.filter(ServiceRequest.status == status)
    if priority:
        query_obj = query_obj.filter(ServiceRequest.priority == priority)
    if category:
        query_obj = query_obj.filter(ServiceRequest.service_category.ilike(f"%{category}%"))
    
    # Sort by priority and created date
    query_obj = query_obj.order_by(
        ServiceRequest.priority.desc(),
        ServiceRequest.created_at.desc()
    )
    
    # Pagination
    total_count = query_obj.count()
    offset = (page - 1) * page_size
    requests = query_obj.offset(offset).limit(page_size).all()
    
    # Add assignments count for each request
    requests_with_counts = []
    for request in requests:
        assignments_count = db.query(TaskAssignment).filter(
            TaskAssignment.service_request_id == request.id
        ).count()
        
        request.assignments_count = assignments_count
        requests_with_counts.append(ServiceRequestResponse.model_validate(request))
    
    return {
        "requests": requests_with_counts,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total_count / page_size)
    }


@router.post("/admin/assign-task", response_model=TaskAssignmentResponse)
async def assign_task_to_professional(
    assignment: TaskAssignmentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_superuser)
) -> Any:
    """
    Assign a service request to a professional.
    """
    # Verify service request exists
    service_request = db.query(ServiceRequest).filter(
        ServiceRequest.id == assignment.service_request_id
    ).first()
    
    if not service_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found"
        )
    
    # Verify professional exists and is verified
    professional = db.query(ProzProfile).filter(
        and_(
            ProzProfile.id == assignment.proz_id,
            ProzProfile.verification_status == "verified"
        )
    ).first()
    
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional not found or not verified"
        )
    
    # Check if already assigned to this professional
    existing_assignment = db.query(TaskAssignment).filter(
        and_(
            TaskAssignment.service_request_id == assignment.service_request_id,
            TaskAssignment.proz_id == assignment.proz_id
        )
    ).first()
    
    if existing_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task already assigned to this professional"
        )
    
    # Create assignment
    task_assignment = TaskAssignment(
        service_request_id=assignment.service_request_id,
        proz_id=assignment.proz_id,
        assigned_by_user_id=current_user.id,
        assignment_notes=assignment.assignment_notes,
        estimated_hours=assignment.estimated_hours,
        proposed_rate=assignment.proposed_rate,
        due_date=assignment.due_date,
        status=TaskStatus.ASSIGNED
    )
    
    db.add(task_assignment)
    
    # Update service request status
    service_request.status = TaskStatus.ASSIGNED
    service_request.updated_at = datetime.utcnow()
    
    # Create notification for professional
    notification = TaskNotification(
        proz_id=assignment.proz_id,
        task_assignment_id=task_assignment.id,
        title=f"New Task Assignment: {service_request.service_title}",
        message=f"You have been assigned a new task from {service_request.company_name}. "
                f"Please review the details and respond within 24 hours.",
        notification_type="task_assigned"
    )
    
    db.add(notification)
    db.commit()
    db.refresh(task_assignment)
    
    # Send email notification in background
    background_tasks.add_task(
        send_assignment_notification,
        professional.email,
        service_request.service_title,
        service_request.company_name
    )
    
    # Build response
    response_data = TaskAssignmentResponse.model_validate(task_assignment)
    response_data.service_request = ServiceRequestResponse.model_validate(service_request)
    response_data.professional_name = f"{professional.first_name} {professional.last_name}"
    response_data.professional_email = professional.email
    
    return response_data


@router.get("/admin/assignments", response_model=dict)
async def get_task_assignments_admin(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    proz_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_superuser)
) -> Any:
    """
    Get all task assignments for admin overview.
    """
    query_obj = db.query(TaskAssignment).join(ServiceRequest).join(ProzProfile)
    
    if status:
        query_obj = query_obj.filter(TaskAssignment.status == status)
    if proz_id:
        query_obj = query_obj.filter(TaskAssignment.proz_id == proz_id)
    
    query_obj = query_obj.order_by(desc(TaskAssignment.assigned_at))
    
    total_count = query_obj.count()
    offset = (page - 1) * page_size
    assignments = query_obj.offset(offset).limit(page_size).all()
    
    # Build response with full details
    assignments_response = []
    for assignment in assignments:
        response_data = TaskAssignmentResponse.model_validate(assignment)
        response_data.service_request = ServiceRequestResponse.model_validate(assignment.service_request)
        response_data.professional_name = f"{assignment.professional.first_name} {assignment.professional.last_name}"
        response_data.professional_email = assignment.professional.email
        assignments_response.append(response_data)
    
    return {
        "assignments": assignments_response,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total_count / page_size)
    }


@router.get("/admin/stats", response_model=AdminTaskStatsResponse)
async def get_admin_task_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_superuser)
) -> Any:
    """
    Get task management statistics for admin dashboard.
    """
    total_requests = db.query(ServiceRequest).count()
    pending_requests = db.query(ServiceRequest).filter(
        ServiceRequest.status == TaskStatus.PENDING
    ).count()
    assigned_requests = db.query(ServiceRequest).filter(
        ServiceRequest.status.in_([TaskStatus.ASSIGNED, TaskStatus.ACCEPTED, TaskStatus.IN_PROGRESS])
    ).count()
    completed_requests = db.query(ServiceRequest).filter(
        ServiceRequest.status == TaskStatus.COMPLETED
    ).count()
    urgent_requests = db.query(ServiceRequest).filter(
        ServiceRequest.priority == TaskPriority.URGENT
    ).count()
    
    # Unassigned requests (no assignments)
    unassigned_requests = db.query(ServiceRequest).filter(
        and_(
            ServiceRequest.status == TaskStatus.PENDING,
            ~ServiceRequest.assignments.any()
        )
    ).count()
    
    # Active professionals (have assignments in last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_professionals = db.query(ProzProfile).join(TaskAssignment).filter(
        TaskAssignment.assigned_at >= thirty_days_ago
    ).distinct().count()
    
    # Requests this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    requests_this_week = db.query(ServiceRequest).filter(
        ServiceRequest.created_at >= week_ago
    ).count()
    
    return AdminTaskStatsResponse(
        total_requests=total_requests,
        pending_requests=pending_requests,
        assigned_requests=assigned_requests,
        completed_requests=completed_requests,
        urgent_requests=urgent_requests,
        unassigned_requests=unassigned_requests,
        active_professionals=active_professionals,
        requests_this_week=requests_this_week
    )


# ==================== PROFESSIONAL ENDPOINTS ====================

@router.get("/professional/tasks", response_model=List[ProfessionalTaskResponse])
async def get_professional_tasks(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
) -> Any:
    """
    Get tasks assigned to the current professional.
    """
    # Get professional profile
    professional = db.query(ProzProfile).filter(
        ProzProfile.email == current_user.email
    ).first()
    
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found"
        )
    
    # Get assignments
    query_obj = db.query(TaskAssignment).join(ServiceRequest).filter(
        TaskAssignment.proz_id == professional.id
    )
    
    if status:
        query_obj = query_obj.filter(TaskAssignment.status == status)
    
    assignments = query_obj.order_by(desc(TaskAssignment.assigned_at)).all()
    
    # Build response
    tasks = []
    for assignment in assignments:
        request = assignment.service_request
        budget_range = None
        if request.budget_min and request.budget_max:
            budget_range = f"${request.budget_min:,.0f} - ${request.budget_max:,.0f}"
        elif request.budget_min:
            budget_range = f"${request.budget_min:,.0f}+"
        
        task = ProfessionalTaskResponse(
            assignment_id=assignment.id,
            service_title=request.service_title,
            company_name=request.company_name,
            client_name=request.client_name,
            service_description=request.service_description,
            service_category=request.service_category,
            budget_range=budget_range,
            estimated_hours=assignment.estimated_hours,
            proposed_rate=assignment.proposed_rate,
            status=assignment.status,
            priority=request.priority,
            assignment_notes=assignment.assignment_notes,
            assigned_at=assignment.assigned_at,
            due_date=assignment.due_date,
            deadline=request.deadline,
            is_remote=request.remote_work_allowed
        )
        tasks.append(task)
    
    return tasks


@router.post("/professional/tasks/{assignment_id}/respond", response_model=dict)
async def respond_to_task_assignment(
    assignment_id: str,
    response: TaskResponseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
) -> Any:
    """
    Professional responds to task assignment (accept/reject/request info).
    """
    # Get professional profile
    professional = db.query(ProzProfile).filter(
        ProzProfile.email == current_user.email
    ).first()
    
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found"
        )
    
    # Get assignment
    assignment = db.query(TaskAssignment).filter(
        and_(
            TaskAssignment.id == assignment_id,
            TaskAssignment.proz_id == professional.id
        )
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Update assignment based on response
    if response.response_action == "accept":
        assignment.status = TaskStatus.ACCEPTED
        message = f"Task accepted by {professional.first_name} {professional.last_name}"
    elif response.response_action == "reject":
        assignment.status = TaskStatus.REJECTED
        message = f"Task rejected by {professional.first_name} {professional.last_name}"
    else:
        message = f"Info requested by {professional.first_name} {professional.last_name}"
    
    assignment.proz_response = response.response_message
    assignment.proz_response_at = datetime.utcnow()
    
    # Update service request status if needed
    if response.response_action == "accept":
        assignment.service_request.status = TaskStatus.ACCEPTED
    
    db.commit()
    
    return {
        "success": True,
        "message": message,
        "assignment_status": assignment.status,
        "response_recorded": True
    }


@router.get("/professional/notifications", response_model=List[NotificationResponse])
async def get_professional_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
) -> Any:
    """
    Get notifications for the current professional.
    """
    # Get professional profile
    professional = db.query(ProzProfile).filter(
        ProzProfile.email == current_user.email
    ).first()
    
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found"
        )
    
    # Get notifications
    query_obj = db.query(TaskNotification).filter(
        TaskNotification.proz_id == professional.id
    )
    
    if unread_only:
        query_obj = query_obj.filter(TaskNotification.is_read == False)
    
    notifications = query_obj.order_by(
        desc(TaskNotification.created_at)
    ).limit(limit).all()
    
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.post("/professional/notifications/{notification_id}/mark-read", response_model=dict)
async def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
) -> Any:
    """
    Mark a notification as read.
    """
    # Get professional profile
    professional = db.query(ProzProfile).filter(
        ProzProfile.email == current_user.email
    ).first()
    
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found"
        )
    
    # Get notification
    notification = db.query(TaskNotification).filter(
        and_(
            TaskNotification.id == notification_id,
            TaskNotification.proz_id == professional.id
        )
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Mark as read
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "Notification marked as read",
        "notification_id": notification_id
    }


@router.get("/professional/dashboard-stats", response_model=DashboardStatsResponse)
async def get_professional_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
) -> Any:
    """
    Get dashboard statistics for the current professional.
    """
    # Get professional profile
    professional = db.query(ProzProfile).filter(
        ProzProfile.email == current_user.email
    ).first()
    
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found"
        )
    
    # Calculate stats
    total_assignments = db.query(TaskAssignment).filter(
        TaskAssignment.proz_id == professional.id
    ).count()
    
    pending_assignments = db.query(TaskAssignment).filter(
        and_(
            TaskAssignment.proz_id == professional.id,
            TaskAssignment.status == TaskStatus.ASSIGNED
        )
    ).count()
    
    active_assignments = db.query(TaskAssignment).filter(
        and_(
            TaskAssignment.proz_id == professional.id,
            TaskAssignment.status.in_([TaskStatus.ACCEPTED, TaskStatus.IN_PROGRESS])
        )
    ).count()
    
    completed_assignments = db.query(TaskAssignment).filter(
        and_(
            TaskAssignment.proz_id == professional.id,
            TaskAssignment.status == TaskStatus.COMPLETED
        )
    ).count()
    
    unread_notifications = db.query(TaskNotification).filter(
        and_(
            TaskNotification.proz_id == professional.id,
            TaskNotification.is_read == False
        )
    ).count()
    
    # Calculate earnings (simplified - would need payment tracking)
    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)
    
    # This week earnings (based on completed tasks - simplified calculation)
    this_week_completed = db.query(TaskAssignment).filter(
        and_(
            TaskAssignment.proz_id == professional.id,
            TaskAssignment.status == TaskStatus.COMPLETED,
            TaskAssignment.completed_at >= week_ago
        )
    ).all()
    
    this_week_earnings = sum([
        (assignment.estimated_hours or 0) * (assignment.proposed_rate or 0)
        for assignment in this_week_completed
    ])
    
    # This month earnings
    this_month_completed = db.query(TaskAssignment).filter(
        and_(
            TaskAssignment.proz_id == professional.id,
            TaskAssignment.status == TaskStatus.COMPLETED,
            TaskAssignment.completed_at >= month_ago
        )
    ).all()
    
    this_month_earnings = sum([
        (assignment.estimated_hours or 0) * (assignment.proposed_rate or 0)
        for assignment in this_month_completed
    ])
    
    return DashboardStatsResponse(
        total_assignments=total_assignments,
        pending_assignments=pending_assignments,
        active_assignments=active_assignments,
        completed_assignments=completed_assignments,
        unread_notifications=unread_notifications,
        this_week_earnings=this_week_earnings,
        this_month_earnings=this_month_earnings,
        average_rating=professional.rating or 0.0
    )


@router.post("/professional/tasks/{assignment_id}/update-status", response_model=dict)
async def update_task_status(
    assignment_id: str,
    new_status: str = Query(..., description="New status: in_progress, completed"),
    notes: Optional[str] = Query(None, description="Update notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
) -> Any:
    """
    Update task status (mark as in progress, completed, etc.).
    """
    # Get professional profile
    professional = db.query(ProzProfile).filter(
        ProzProfile.email == current_user.email
    ).first()
    
    if not professional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found"
        )
    
    # Get assignment
    assignment = db.query(TaskAssignment).filter(
        and_(
            TaskAssignment.id == assignment_id,
            TaskAssignment.proz_id == professional.id
        )
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Validate status transition
    valid_statuses = ["in_progress", "completed"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    # Update status
    old_status = assignment.status
    assignment.status = TaskStatus(new_status)
    
    if new_status == "completed":
        assignment.completed_at = datetime.utcnow()
        assignment.service_request.status = TaskStatus.COMPLETED
    elif new_status == "in_progress":
        assignment.service_request.status = TaskStatus.IN_PROGRESS
    
    # Add notes to proz_response if provided
    if notes:
        existing_response = assignment.proz_response or ""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        assignment.proz_response = f"{existing_response}\n[{timestamp}] Status update: {notes}".strip()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Task status updated from {old_status} to {new_status}",
        "assignment_id": assignment_id,
        "new_status": new_status
    }


# ==================== HELPER FUNCTIONS ====================

async def send_assignment_notification(
    professional_email: str,
    service_title: str,
    company_name: str
):
    """
    Send email notification to professional about new task assignment.
    This is a background task.
    """
    # TODO: Implement email sending logic
    # For now, just log the notification
    print(f"📧 Email notification sent to {professional_email}")
    print(f"   Subject: New Task Assignment: {service_title}")
    print(f"   Company: {company_name}")
    
    # In production, you would use an email service like:
    # - SendGrid
    # - AWS SES
    # - FastAPI-Mail
    # etc.


@router.get("/auto-suggest-professionals", response_model=List[dict])
async def auto_suggest_professionals(
    service_request_id: str,
    limit: int = Query(5, le=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_superuser)
) -> Any:
    """
    Auto-suggest professionals for a service request based on skills, location, etc.
    """
    # Get service request
    service_request = db.query(ServiceRequest).filter(
        ServiceRequest.id == service_request_id
    ).first()
    
    if not service_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found"
        )
    
    # Find matching professionals
    query_obj = db.query(ProzProfile).filter(
        ProzProfile.verification_status == "verified"
    )
    
    # Match by specialty/category
    if service_request.service_category:
        query_obj = query_obj.join(ProzSpecialty).join(Specialty).filter(
            Specialty.name.ilike(f"%{service_request.service_category}%")
        )
    
    # Match by location (if not remote)
    if not service_request.remote_work_allowed and service_request.location_preference:
        query_obj = query_obj.filter(
            ProzProfile.location.ilike(f"%{service_request.location_preference}%")
        )
    
    # Match by hourly rate (if budget specified)
    if service_request.budget_max:
        # Assuming budget is total project, estimate hourly based on expected duration
        estimated_hours = 40  # Default estimate, could be smarter
        max_hourly = service_request.budget_max / estimated_hours
        query_obj = query_obj.filter(
            or_(
                ProzProfile.hourly_rate <= max_hourly,
                ProzProfile.hourly_rate.is_(None)
            )
        )
    
    # Order by rating and exclude already assigned
    assigned_proz_ids = db.query(TaskAssignment.proz_id).filter(
        TaskAssignment.service_request_id == service_request_id
    ).subquery()
    
    professionals = query_obj.filter(
        ~ProzProfile.id.in_(assigned_proz_ids)
    ).order_by(
        desc(ProzProfile.rating),
        desc(ProzProfile.years_experience)
    ).limit(limit).all()
    
    # Build suggestions with match reasons
    suggestions = []
    for professional in professionals:
        # Get specialties
        specialties = db.query(Specialty.name).join(ProzSpecialty).filter(
            ProzSpecialty.proz_id == professional.id
        ).all()
        
        match_reasons = []
        if any(service_request.service_category.lower() in s.name.lower() for s in specialties):
            match_reasons.append("Matching specialty")
        if professional.location and service_request.location_preference:
            if service_request.location_preference.lower() in professional.location.lower():
                match_reasons.append("Local professional")
        if professional.rating >= 4.0:
            match_reasons.append("High rating")
        
        suggestions.append({
            "id": str(professional.id),
            "name": f"{professional.first_name} {professional.last_name}",
            "email": professional.email,
            "location": professional.location,
            "rating": professional.rating,
            "years_experience": professional.years_experience,
            "hourly_rate": professional.hourly_rate,
            "specialties": [s.name for s in specialties],
            "match_reasons": match_reasons,
            "profile_image_url": professional.profile_image_url
        })
    
    return suggestions