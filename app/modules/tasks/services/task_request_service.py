# app/modules/tasks/services/task_request_service.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime
import logging

from app.modules.tasks.models.task import ServiceRequest, TaskAssignment, TaskNotification
from app.modules.tasks.models.task_enums import TaskStatusEnum, TaskPriorityEnum
from app.modules.proz.models.proz import ProzProfile
from app.modules.tasks.schemas.task_request import (
    BusinessTaskRequestCreate, 
    TaskAssignmentProposalCreate,
    BusinessTaskRequestResponse,
    TaskAssignmentProposalResponse,
    TaskAssignmentResponse
)
from app.services.email_service import EmailService
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class TaskRequestService:
    """Service for handling business task requests and assignments"""
    
    def __init__(self):
        self.email_service = EmailService()
    
    def create_business_task_request(
        self, 
        db: Session, 
        request_data: BusinessTaskRequestCreate
    ) -> BusinessTaskRequestResponse:
        """Create a new business task request"""
        try:
            # Create service request
            service_request = ServiceRequest(**request_data.model_dump())
            
            db.add(service_request)
            db.commit()
            db.refresh(service_request)
            
            logger.info(f"✅ Business task request created: {service_request.id}")
            
            # Return response with assignment counts
            response_data = BusinessTaskRequestResponse.model_validate(service_request)
            response_data.assignments_count = 0
            response_data.accepted_assignments_count = 0
            
            return response_data
            
        except Exception as e:
            logger.error(f"❌ Error creating business task request: {str(e)}")
            db.rollback()
            raise
    
    def get_business_task_requests(
        self, 
        db: Session, 
        page: int = 1, 
        limit: int = 20,
        status: Optional[TaskStatusEnum] = None,
        priority: Optional[TaskPriorityEnum] = None,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get business task requests with filtering and pagination"""
        try:
            query = db.query(ServiceRequest)
            
            # Apply filters
            if status:
                query = query.filter(ServiceRequest.status == status.value)
            if priority:
                query = query.filter(ServiceRequest.priority == priority.value)
            if company_name:
                query = query.filter(ServiceRequest.company_name.ilike(f"%{company_name}%"))
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            skip = (page - 1) * limit
            requests = query.offset(skip).limit(limit).all()
            
            # Convert to response format
            response_requests = []
            for request in requests:
                # Get assignment counts
                assignments_count = db.query(TaskAssignment).filter(
                    TaskAssignment.service_request_id == request.id
                ).count()
                
                accepted_assignments_count = db.query(TaskAssignment).filter(
                    and_(
                        TaskAssignment.service_request_id == request.id,
                        TaskAssignment.status == TaskStatusEnum.ACCEPTED.value
                    )
                ).count()
                
                response_data = BusinessTaskRequestResponse.model_validate(request)
                response_data.assignments_count = assignments_count
                response_data.accepted_assignments_count = accepted_assignments_count
                response_requests.append(response_data)
            
            return {
                "requests": response_requests,
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting business task requests: {str(e)}")
            raise
    
    def create_task_assignment_proposal(
        self, 
        db: Session, 
        assignment_data: TaskAssignmentProposalCreate,
        assigned_by_user_id: str
    ) -> TaskAssignmentProposalResponse:
        """Create a task assignment proposal and send email notification"""
        try:
            # Verify service request exists
            service_request = db.query(ServiceRequest).filter(
                ServiceRequest.id == assignment_data.service_request_id
            ).first()
            
            if not service_request:
                raise NotFoundException("Service request not found")
            
            # Verify professional exists
            professional = db.query(ProzProfile).filter(
                ProzProfile.id == assignment_data.proz_id
            ).first()
            
            if not professional:
                raise NotFoundException("Professional not found")
            
            # Check if assignment already exists
            existing_assignment = db.query(TaskAssignment).filter(
                and_(
                    TaskAssignment.service_request_id == assignment_data.service_request_id,
                    TaskAssignment.proz_id == assignment_data.proz_id
                )
            ).first()
            
            if existing_assignment:
                raise ValueError("Task assignment already exists for this professional")
            
            # Create task assignment
            task_assignment = TaskAssignment(
                service_request_id=assignment_data.service_request_id,
                proz_id=assignment_data.proz_id,
                assigned_by_user_id=assigned_by_user_id,
                assignment_notes=assignment_data.assignment_notes,
                estimated_hours=assignment_data.estimated_hours,
                proposed_rate=assignment_data.proposed_rate,
                due_date=assignment_data.due_date,
                status=TaskStatusEnum.ASSIGNED.value
            )
            
            db.add(task_assignment)
            db.commit()
            db.refresh(task_assignment)
            
            # Send email notification to professional
            self._send_assignment_notification_email(
                professional=professional,
                service_request=service_request,
                task_assignment=task_assignment
            )
            
            logger.info(f"✅ Task assignment created: {task_assignment.id}")
            
            # Create response with additional details
            response_data = TaskAssignmentProposalResponse(
                id=str(task_assignment.id),
                service_request_id=str(task_assignment.service_request_id),
                proz_id=str(task_assignment.proz_id),
                assignment_notes=task_assignment.assignment_notes,
                estimated_hours=task_assignment.estimated_hours,
                proposed_rate=task_assignment.proposed_rate,
                status=TaskStatusEnum(task_assignment.status),
                due_date=task_assignment.due_date,
                assigned_at=task_assignment.assigned_at,
                proz_response=task_assignment.proz_response,
                proz_response_at=task_assignment.proz_response_at,
                service_title=service_request.service_title,
                service_description=service_request.service_description,
                company_name=service_request.company_name,
                professional_name=f"{professional.first_name} {professional.last_name}",
                professional_email=professional.email
            )
            
            return response_data
            
        except Exception as e:
            logger.error(f"❌ Error creating task assignment: {str(e)}")
            db.rollback()
            raise
    
    def _send_assignment_notification_email(
        self, 
        professional: ProzProfile, 
        service_request: ServiceRequest,
        task_assignment: TaskAssignment
    ) -> None:
        """Send email notification to professional about task assignment"""
        try:
            # Create email content
            subject = f"New Task Assignment: {service_request.service_title}"
            
            # Calculate estimated total cost if both rate and hours are provided
            estimated_total = None
            if task_assignment.estimated_hours and task_assignment.proposed_rate:
                estimated_total = float(task_assignment.estimated_hours * task_assignment.proposed_rate)
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>New Task Assignment</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background-color: #4CAF50;
                        color: white;
                        padding: 20px;
                        text-align: center;
                        border-radius: 5px 5px 0 0;
                    }}
                    .content {{
                        background-color: #f9f9f9;
                        padding: 30px;
                        border-radius: 0 0 5px 5px;
                    }}
                    .task-details {{
                        background-color: #fff;
                        padding: 20px;
                        border-radius: 5px;
                        margin: 20px 0;
                    }}
                    .button {{
                        display: inline-block;
                        background-color: #4CAF50;
                        color: white;
                        padding: 12px 30px;
                        text-decoration: none;
                        border-radius: 5px;
                        margin: 20px 0;
                    }}
                    .footer {{
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #ddd;
                        font-size: 12px;
                        color: #666;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>New Task Assignment</h1>
                </div>
                <div class="content">
                    <h2>Hello {professional.first_name},</h2>
                    <p>You have been assigned a new task. Here are the details:</p>
                    
                    <div class="task-details">
                        <h3>Task Details</h3>
                        <p><strong>Service:</strong> {service_request.service_title}</p>
                        <p><strong>Company:</strong> {service_request.company_name}</p>
                        <p><strong>Description:</strong> {service_request.service_description}</p>
                        <p><strong>Category:</strong> {service_request.service_category}</p>
                        
                        {f'<p><strong>Location:</strong> {service_request.location_preference}</p>' if service_request.location_preference else ''}
                        {f'<p><strong>Deadline:</strong> {service_request.deadline.strftime("%B %d, %Y") if service_request.deadline else "Not specified"}</p>' if service_request.deadline else ''}
                        
                        <h3>Assignment Details</h3>
                        {f'<p><strong>Estimated Hours:</strong> {task_assignment.estimated_hours}</p>' if task_assignment.estimated_hours else ''}
                        {f'<p><strong>Proposed Rate:</strong> ${task_assignment.proposed_rate}/hour</p>' if task_assignment.proposed_rate else ''}
                        {f'<p><strong>Estimated Total:</strong> ${estimated_total:,.2f}</p>' if estimated_total else ''}
                        {f'<p><strong>Due Date:</strong> {task_assignment.due_date.strftime("%B %d, %Y") if task_assignment.due_date else "Not specified"}</p>' if task_assignment.due_date else ''}
                        
                        {f'<p><strong>Assignment Notes:</strong> {task_assignment.assignment_notes}</p>' if task_assignment.assignment_notes else ''}
                    </div>
                    
                    <p>Please log in to your account to accept or decline this assignment.</p>
                    
                    <div style="text-align: center;">
                        <a href="http://localhost:3000/professional/tasks" class="button">View Task Details</a>
                    </div>
                </div>
                <div class="footer">
                    <p>This email was sent from your task management system</p>
                    <p>Please do not reply to this email.</p>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            New Task Assignment
            
            Hello {professional.first_name},
            
            You have been assigned a new task:
            
            Service: {service_request.service_title}
            Company: {service_request.company_name}
            Description: {service_request.service_description}
            Category: {service_request.service_category}
            
            {f'Location: {service_request.location_preference}' if service_request.location_preference else ''}
            {f'Deadline: {service_request.deadline.strftime("%B %d, %Y") if service_request.deadline else "Not specified"}' if service_request.deadline else ''}
            
            Assignment Details:
            {f'Estimated Hours: {task_assignment.estimated_hours}' if task_assignment.estimated_hours else ''}
            {f'Proposed Rate: ${task_assignment.proposed_rate}/hour' if task_assignment.proposed_rate else ''}
            {f'Estimated Total: ${estimated_total:,.2f}' if estimated_total else ''}
            {f'Due Date: {task_assignment.due_date.strftime("%B %d, %Y") if task_assignment.due_date else "Not specified"}' if task_assignment.due_date else ''}
            
            {f'Assignment Notes: {task_assignment.assignment_notes}' if task_assignment.assignment_notes else ''}
            
            Please log in to your account to accept or decline this assignment.
            
            Best regards,
            Task Management System
            """
            
            # Send email via Mailtrap if available, else SMTP, else log in dev mode
            try:
                if self.email_service.mailtrap_api_key:
                    self.email_service._send_mailtrap_email(
                        to_email=professional.email,
                        to_name=f"{professional.first_name} {professional.last_name}".strip() or professional.email,
                        subject=subject,
                        text_body=text_body,
                        html_body=html_body,
                    )
                    logger.info(f"📧 Task assignment email sent via Mailtrap to {professional.email}")
                elif self.email_service.smtp_configured and not self.email_service.development_mode:
                    self.email_service._send_smtp_email(
                        to_email=professional.email,
                        subject=subject,
                        html_body=html_body,
                        text_body=text_body
                    )
                    logger.info(f"📧 Task assignment email sent via SMTP to {professional.email}")
                else:
                    logger.info(f"📧 DEVELOPMENT MODE - Task assignment email for {professional.email}")
                    logger.info(f"📧 Subject: {subject}")
                    print(f"📧 DEVELOPMENT MODE - Task assignment email for {professional.email}")
                    print(f"📧 Subject: {subject}")
            except Exception as send_err:
                logger.error(f"❌ Error sending assignment notification email: {send_err}")
            
        except Exception as e:
            logger.error(f"❌ Error sending assignment notification email: {str(e)}")
            # Don't raise the exception as email failure shouldn't break the assignment
    
    def get_task_assignments_for_professional(
        self, 
        db: Session, 
        professional_email: str,
        status: Optional[TaskStatusEnum] = None
    ) -> List[TaskAssignmentResponse]:
        """Get task assignments for a specific professional"""
        try:
            # Find professional by email
            professional = db.query(ProzProfile).filter(
                ProzProfile.email == professional_email
            ).first()
            
            if not professional:
                raise NotFoundException("Professional not found")
            
            # Build query
            query = db.query(TaskAssignment).filter(
                TaskAssignment.proz_id == professional.id
            )
            
            if status:
                query = query.filter(TaskAssignment.status == status.value)
            
            assignments = query.order_by(TaskAssignment.assigned_at.desc()).all()
            
            # Convert to response format
            response_assignments = []
            for assignment in assignments:
                response_data = TaskAssignmentResponse.model_validate(assignment)
                response_assignments.append(response_data)
            
            return response_assignments
            
        except Exception as e:
            logger.error(f"❌ Error getting task assignments for professional: {str(e)}")
            raise
    
    def update_task_assignment_status(
        self, 
        db: Session, 
        assignment_id: str,
        new_status: TaskStatusEnum,
        proz_response: Optional[str] = None,
        professional_email: str = None
    ) -> TaskAssignmentResponse:
        """Update task assignment status (for professional responses)"""
        try:
            # Get assignment
            assignment = db.query(TaskAssignment).filter(
                TaskAssignment.id == assignment_id
            ).first()
            
            if not assignment:
                raise NotFoundException("Task assignment not found")
            
            # Verify professional owns this assignment
            if professional_email:
                professional = db.query(ProzProfile).filter(
                    and_(
                        ProzProfile.email == professional_email,
                        ProzProfile.id == assignment.proz_id
                    )
                ).first()
                
                if not professional:
                    raise ValueError("You are not authorized to update this assignment")
            
            # Update assignment
            assignment.status = new_status.value
            if proz_response:
                assignment.proz_response = proz_response
                assignment.proz_response_at = datetime.utcnow()
            
            if new_status == TaskStatusEnum.COMPLETED:
                assignment.completed_at = datetime.utcnow()
            
            db.commit()
            db.refresh(assignment)
            
            logger.info(f"✅ Task assignment status updated: {assignment_id} -> {new_status.value}")
            
            return TaskAssignmentResponse.model_validate(assignment)
            
        except Exception as e:
            logger.error(f"❌ Error updating task assignment status: {str(e)}")
            db.rollback()
            raise
