# app/modules/tasks/controllers/task_request_controller.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.services.auth_service import get_current_user, get_current_superuser
from app.modules.auth.models.user import User
from app.modules.tasks.services.task_request_service import TaskRequestService
from app.services.notification_service import NotificationService
from app.modules.tasks.schemas.task_request import (
    BusinessTaskRequestCreate,
    BusinessTaskRequestResponse,
    TaskAssignmentProposalCreate,
    TaskAssignmentProposalResponse,
    TaskAssignmentResponse,
    TaskAssignmentUpdate
)
from app.modules.tasks.models.task_enums import TaskStatusEnum, TaskPriorityEnum
from app.modules.tasks.models.task import ServiceRequest, TaskAssignment
from sqlalchemy import and_

router = APIRouter()
task_request_service = TaskRequestService()


# ==================== PUBLIC ENDPOINTS ====================

@router.post("/business-requests", response_model=BusinessTaskRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_business_task_request(
    request: BusinessTaskRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new business task request.
    
    This endpoint allows businesses to request services like:
    - CCTV camera installation/repair
    - IT support
    - Maintenance services
    - Any other professional services
    
    The request will be reviewed by admin and assigned to appropriate professionals.
    """
    try:
        response = task_request_service.create_business_task_request(db, request)
        
        # Send email notification to admin about new service request
        admin_user = db.query(User).filter(User.is_superuser == True).first()
        if admin_user:
            background_tasks.add_task(
                send_service_request_notification,
                admin_user.email,
                f"{admin_user.first_name} {admin_user.last_name}",
                request.company_name,
                request.client_name,
                request.client_email,
                request.service_title,
                request.service_description,
                request.priority.value if hasattr(request.priority, 'value') else str(request.priority),
                response.created_at.isoformat()
            )
        
        # Always notify primary ops address as requested
        background_tasks.add_task(
            send_service_request_notification,
            "alex@mista.io",
            "Alex",
            request.company_name,
            request.client_name,
            request.client_email,
            request.service_title,
            request.service_description,
            request.priority.value if hasattr(request.priority, 'value') else str(request.priority),
            response.created_at.isoformat()
        )
        
        return response
        
    except Exception as e:
        print(f"❌ Error creating business task request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task request. Please try again later."
        )


@router.get("/business-requests/{request_id}", response_model=BusinessTaskRequestResponse)
async def get_business_task_request(
    request_id: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Get business task request details.
    
    This endpoint allows businesses to check the status of their requests.
    """
    try:
        service_request = db.query(ServiceRequest).filter(
            ServiceRequest.id == request_id
        ).first()
        
        if not service_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task request not found"
            )
        
        # Get assignment counts
        from app.modules.tasks.models.task import TaskAssignment
        assignments_count = db.query(TaskAssignment).filter(
            TaskAssignment.service_request_id == request_id
        ).count()
        
        accepted_assignments_count = db.query(TaskAssignment).filter(
            TaskAssignment.service_request_id == request_id,
            TaskAssignment.status == TaskStatusEnum.ACCEPTED.value
        ).count()
        
        response = BusinessTaskRequestResponse.model_validate(service_request)
        response.assignments_count = assignments_count
        response.accepted_assignments_count = accepted_assignments_count
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting business task request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task request."
        )


# ==================== ADMIN ENDPOINTS ====================

@router.get("/admin/business-requests", response_model=Dict[str, Any])
async def get_business_task_requests_admin(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[TaskStatusEnum] = Query(None, description="Filter by status"),
    priority: Optional[TaskPriorityEnum] = Query(None, description="Filter by priority"),
    company_name: Optional[str] = Query(None, description="Filter by company name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Get business task requests for admin review.
    
    This endpoint allows admins to view and manage all business task requests.
    """
    try:
        result = task_request_service.get_business_task_requests(
            db=db,
            page=page,
            limit=limit,
            status=status,
            priority=priority,
            company_name=company_name
        )
        return result
        
    except Exception as e:
        print(f"❌ Error getting business task requests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task requests."
        )


@router.post("/admin/assign-task", response_model=TaskAssignmentProposalResponse, status_code=status.HTTP_201_CREATED)
async def assign_task_to_professional(
    assignment: TaskAssignmentProposalCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Assign a task to a professional (Admin only).
    
    This endpoint allows admins to assign business task requests to professionals.
    An email notification will be sent to the professional with task details.
    """
    try:
        response = task_request_service.create_task_assignment_proposal(
            db=db,
            assignment_data=assignment,
            assigned_by_user_id=str(current_user.id)
        )
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error assigning task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign task. Please try again later."
        )


@router.get("/admin/task-assignments", response_model=List[TaskAssignmentProposalResponse])
async def get_task_assignments_admin(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[TaskStatusEnum] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Get all task assignments for admin review.
    """
    try:
        from app.modules.tasks.models.task import TaskAssignment
        from app.modules.tasks.models.task import ServiceRequest
        from app.modules.proz.models.proz import ProzProfile
        
        query = db.query(TaskAssignment)
        
        if status:
            query = query.filter(TaskAssignment.status == status.value)
        
        skip = (page - 1) * limit
        assignments = query.offset(skip).limit(limit).all()
        
        response_assignments = []
        for assignment in assignments:
            # Get related data
            service_request = db.query(ServiceRequest).filter(
                ServiceRequest.id == assignment.service_request_id
            ).first()
            
            professional = db.query(ProzProfile).filter(
                ProzProfile.id == assignment.proz_id
            ).first()
            
            if service_request and professional:
                response_data = TaskAssignmentProposalResponse(
                    id=str(assignment.id),
                    service_request_id=str(assignment.service_request_id),
                    proz_id=str(assignment.proz_id),
                    assignment_notes=assignment.assignment_notes,
                    estimated_hours=assignment.estimated_hours,
                    proposed_rate=assignment.proposed_rate,
                    status=TaskStatusEnum(assignment.status),
                    due_date=assignment.due_date,
                    assigned_at=assignment.assigned_at,
                    proz_response=assignment.proz_response,
                    proz_response_at=assignment.proz_response_at,
                    service_title=service_request.service_title,
                    service_description=service_request.service_description,
                    company_name=service_request.company_name,
                    professional_name=f"{professional.first_name} {professional.last_name}",
                    professional_email=professional.email
                )
                response_assignments.append(response_data)
        
        return response_assignments
        
    except Exception as e:
        print(f"❌ Error getting task assignments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task assignments."
        )


# ==================== PROFESSIONAL ENDPOINTS ====================

@router.get("/professional/my-assignments", response_model=List[TaskAssignmentResponse])
async def get_my_task_assignments(
    status: Optional[TaskStatusEnum] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get task assignments for the current professional.
    
    This endpoint allows professionals to view their assigned tasks.
    """
    try:
        assignments = task_request_service.get_task_assignments_for_professional(
            db=db,
            professional_email=current_user.email,
            status=status
        )
        return assignments
        
    except Exception as e:
        print(f"❌ Error getting professional assignments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve your task assignments."
        )


@router.patch("/professional/assignments/{assignment_id}/status", response_model=TaskAssignmentResponse)
async def update_assignment_status(
    assignment_id: str,
    new_status: TaskStatusEnum = Query(..., description="New status: accepted, rejected, in_progress, completed"),
    proz_response: Optional[str] = Query(None, description="Professional response/notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update task assignment status (Professional only).
    
    This endpoint allows professionals to:
    - Accept or reject task assignments
    - Mark tasks as in progress
    - Mark tasks as completed
    """
    try:
        response = task_request_service.update_task_assignment_status(
            db=db,
            assignment_id=assignment_id,
            new_status=new_status,
            proz_response=proz_response,
            professional_email=current_user.email
        )
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error updating assignment status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update assignment status."
        )


@router.get("/professional/assignments/{assignment_id}", response_model=TaskAssignmentResponse)
async def get_assignment_details(
    assignment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get detailed information about a specific task assignment.
    """
    try:
        from app.modules.tasks.models.task import TaskAssignment
        from app.modules.proz.models.proz import ProzProfile
        
        # Get assignment
        assignment = db.query(TaskAssignment).filter(
            TaskAssignment.id == assignment_id
        ).first()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task assignment not found"
            )
        
        # Verify professional owns this assignment
        professional = db.query(ProzProfile).filter(
            and_(
                ProzProfile.email == current_user.email,
                ProzProfile.id == assignment.proz_id
            )
        ).first()
        
        if not professional:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view this assignment"
            )
        
        return TaskAssignmentResponse.model_validate(assignment)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting assignment details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve assignment details."
        )


# ==================== HELPER FUNCTIONS ====================

async def send_service_request_notification(
    admin_email: str,
    admin_name: str,
    company_name: str,
    client_name: str,
    client_email: str,
    service_title: str,
    service_description: str,
    priority: str,
    created_at: str
):
    """
    Send email notification to admin about new service request.
    This is a background task.
    """
    try:
        notification_service = NotificationService()
        result = notification_service.send_service_request_notification(
            admin_email=admin_email,
            admin_name=admin_name,
            company_name=company_name,
            client_name=client_name,
            client_email=client_email,
            service_title=service_title,
            service_description=service_description,
            priority=priority,
            created_at=created_at
        )
        
        if result["success"]:
            print(f"✅ Service request notification sent to {admin_email}")
        else:
            print(f"❌ Failed to send service request notification to {admin_email}: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error sending service request notification to {admin_email}: {str(e)}")
