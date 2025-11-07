# app/modules/tasks/services/task_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uuid

from app.modules.tasks.models.service_request import ServiceRequest
from app.modules.tasks.models.task_enums import TaskStatusEnum, TaskPriorityEnum
from app.modules.tasks.schemas.service_request import ServiceRequestCreate, ServiceRequestUpdate


class TaskService:
    def create_service_request(self, db: Session, service_request_in: ServiceRequestCreate) -> ServiceRequest:
        """Create a new service request"""
        try:
            # Convert Pydantic model to dict
            request_data = service_request_in.model_dump(exclude_unset=True)
            
            # Ensure enums are converted to their string values
            if 'status' in request_data and request_data['status']:
                request_data['status'] = request_data['status'].value if hasattr(request_data['status'], 'value') else request_data['status']
            else:
                request_data['status'] = TaskStatusEnum.PENDING.value  # Use .value to get string
                
            if 'priority' in request_data and request_data['priority']:
                request_data['priority'] = request_data['priority'].value if hasattr(request_data['priority'], 'value') else request_data['priority']
            else:
                request_data['priority'] = TaskPriorityEnum.MEDIUM.value  # Use .value to get string
            
            # Create the service request
            db_service_request = ServiceRequest(**request_data)
            
            db.add(db_service_request)
            db.commit()
            db.refresh(db_service_request)
            
            return db_service_request
            
        except IntegrityError as e:
            db.rollback()
            print(f"Database integrity error: {str(e)}")
            raise ValueError("Failed to create service request due to data constraint violation")
        except Exception as e:
            db.rollback()
            print(f"Error creating service request: {str(e)}")
            raise

    def get_service_request(self, db: Session, request_id: str) -> Optional[ServiceRequest]:
        """Get a service request by ID"""
        try:
            request_uuid = uuid.UUID(request_id)
            return db.query(ServiceRequest).filter(ServiceRequest.id == request_uuid).first()
        except ValueError:
            return None

    def get_service_requests(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[TaskStatusEnum] = None,
        priority: Optional[TaskPriorityEnum] = None
    ) -> List[ServiceRequest]:
        """Get service requests with optional filtering"""
        query = db.query(ServiceRequest)
        
        if status:
            # Use the enum value (string) for filtering
            query = query.filter(ServiceRequest.status == status.value)
        if priority:
            # Use the enum value (string) for filtering  
            query = query.filter(ServiceRequest.priority == priority.value)
            
        return query.offset(skip).limit(limit).all()

    def update_service_request(
        self, 
        db: Session, 
        request_id: str, 
        service_request_update: ServiceRequestUpdate
    ) -> Optional[ServiceRequest]:
        """Update a service request"""
        try:
            # Get existing request
            db_service_request = self.get_service_request(db, request_id)
            if not db_service_request:
                return None
            
            # Get update data
            update_data = service_request_update.model_dump(exclude_unset=True)
            
            # Convert enum values to strings
            if 'status' in update_data and update_data['status']:
                update_data['status'] = update_data['status'].value if hasattr(update_data['status'], 'value') else update_data['status']
            if 'priority' in update_data and update_data['priority']:
                update_data['priority'] = update_data['priority'].value if hasattr(update_data['priority'], 'value') else update_data['priority']
            
            # Update fields
            for field, value in update_data.items():
                if hasattr(db_service_request, field):
                    setattr(db_service_request, field, value)
            
            db.add(db_service_request)
            db.commit()
            db.refresh(db_service_request)
            
            return db_service_request
            
        except Exception as e:
            db.rollback()
            print(f"Error updating service request: {str(e)}")
            raise

    def delete_service_request(self, db: Session, request_id: str) -> bool:
        """Delete a service request"""
        try:
            db_service_request = self.get_service_request(db, request_id)
            if not db_service_request:
                return False
            
            db.delete(db_service_request)
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            print(f"Error deleting service request: {str(e)}")
            return False