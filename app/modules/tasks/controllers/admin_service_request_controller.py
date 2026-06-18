import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.session import get_db
from app.modules.auth.models.user import User
from app.modules.auth.services.auth_service import get_current_superuser
from app.modules.proz.models.proz import ProzProfile
from app.modules.tasks.models.task import (
    ServiceRequest,
    ServiceRequestMessage,
    ServiceRequestProposal,
    TaskAssignment,
    TaskPriority,
    TaskStatus,
)
from app.modules.tasks.schemas.service_request_admin import (
    ProposalLineItem,
    ServiceRequestAdminDetailResponse,
    ServiceRequestAdminUpdate,
    ServiceRequestMessageCreate,
    ServiceRequestMessageResponse,
    ServiceRequestProposalCreate,
    ServiceRequestProposalResponse,
)
from app.modules.tasks.schemas.task import ServiceRequestResponse, TaskAssignmentResponse
from app.services.notification_service import NotificationService

router = APIRouter()
notification_service = NotificationService()

PROPOSAL_UPLOAD_DIR = Path(settings.UPLOAD_DIR) / "proposals"
ALLOWED_PROPOSAL_EXTENSIONS = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg"}


def _proposal_public_url(token: str) -> str:
    return f"{settings.APP_URL.rstrip('/')}/proposal/{token}"


def _compute_totals(line_items: Optional[List[ProposalLineItem]], tax_rate: float) -> tuple[float, float, float]:
    subtotal = 0.0
    if line_items:
        for item in line_items:
            subtotal += float(item.quantity) * float(item.unit_price)
    tax_amount = round(subtotal * (tax_rate / 100.0), 2)
    total = round(subtotal + tax_amount, 2)
    return subtotal, tax_amount, total


def _serialize_proposal(proposal: ServiceRequestProposal) -> ServiceRequestProposalResponse:
    data = ServiceRequestProposalResponse.model_validate(proposal)
    data.public_url = _proposal_public_url(proposal.public_token)
    return data


def _get_request_or_404(db: Session, request_id: str) -> ServiceRequest:
    service_request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
    if not service_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    return service_request


@router.get("/admin/service-requests/{request_id}", response_model=ServiceRequestAdminDetailResponse)
async def get_service_request_admin_detail(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    service_request = _get_request_or_404(db, request_id)
    assignments_count = db.query(TaskAssignment).filter(
        TaskAssignment.service_request_id == service_request.id
    ).count()
    service_request.assignments_count = assignments_count
    request_data = ServiceRequestResponse.model_validate(service_request)

    assignments = db.query(TaskAssignment).filter(
        TaskAssignment.service_request_id == service_request.id
    ).order_by(TaskAssignment.assigned_at.desc()).all()

    assignment_rows: List[TaskAssignmentResponse] = []
    for assignment in assignments:
        row = TaskAssignmentResponse.model_validate(assignment)
        row.service_request = request_data
        professional = db.query(ProzProfile).filter(ProzProfile.id == assignment.proz_id).first()
        if professional:
            row.professional_name = f"{professional.first_name} {professional.last_name}".strip()
            row.professional_email = professional.email
        assignment_rows.append(row)

    messages = (
        db.query(ServiceRequestMessage)
        .filter(ServiceRequestMessage.service_request_id == service_request.id)
        .order_by(ServiceRequestMessage.created_at.asc())
        .all()
    )
    proposals = (
        db.query(ServiceRequestProposal)
        .filter(ServiceRequestProposal.service_request_id == service_request.id)
        .order_by(ServiceRequestProposal.created_at.desc())
        .all()
    )

    return ServiceRequestAdminDetailResponse(
        request=request_data,
        assignments=assignment_rows,
        messages=[ServiceRequestMessageResponse.model_validate(m) for m in messages],
        proposals=[_serialize_proposal(p) for p in proposals],
    )


@router.patch("/admin/service-requests/{request_id}", response_model=ServiceRequestResponse)
async def update_service_request_admin(
    request_id: str,
    payload: ServiceRequestAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    service_request = _get_request_or_404(db, request_id)

    if payload.status:
        try:
            service_request.status = TaskStatus(payload.status.lower())
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
    if payload.priority:
        try:
            service_request.priority = TaskPriority(payload.priority.lower())
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid priority")
    if payload.admin_notes is not None:
        service_request.admin_notes = payload.admin_notes

    db.commit()
    db.refresh(service_request)
    service_request.assignments_count = db.query(TaskAssignment).filter(
        TaskAssignment.service_request_id == service_request.id
    ).count()
    return ServiceRequestResponse.model_validate(service_request)


@router.post(
    "/admin/service-requests/{request_id}/messages",
    response_model=ServiceRequestMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service_request_message(
    request_id: str,
    payload: ServiceRequestMessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    service_request = _get_request_or_404(db, request_id)
    admin_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or "Prozlab Admin"

    message = ServiceRequestMessage(
        service_request_id=service_request.id,
        author_type="admin",
        author_name=admin_name,
        author_email=current_user.email,
        message_type=payload.message_type,
        subject=payload.subject,
        body=payload.body,
        requested_budget_min=payload.requested_budget_min,
        requested_budget_max=payload.requested_budget_max,
        requested_days=payload.requested_days,
        email_sent=False,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    if payload.send_email_to_client and service_request.client_email:
        background_tasks.add_task(
            notification_service.send_service_request_followup_to_client,
            client_name=service_request.client_name,
            client_email=service_request.client_email,
            service_title=service_request.service_title,
            message_body=payload.body,
            subject=payload.subject,
            requested_budget_min=payload.requested_budget_min,
            requested_budget_max=payload.requested_budget_max,
            requested_days=payload.requested_days,
            request_id=str(service_request.id),
        )
        message.email_sent = True
        db.commit()
        db.refresh(message)

    return ServiceRequestMessageResponse.model_validate(message)


@router.get(
    "/admin/service-requests/{request_id}/messages",
    response_model=List[ServiceRequestMessageResponse],
)
async def list_service_request_messages_admin(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    _get_request_or_404(db, request_id)
    rows = (
        db.query(ServiceRequestMessage)
        .filter(ServiceRequestMessage.service_request_id == request_id)
        .order_by(ServiceRequestMessage.created_at.asc())
        .all()
    )
    return [ServiceRequestMessageResponse.model_validate(row) for row in rows]


@router.post(
    "/admin/service-requests/{request_id}/proposals",
    response_model=ServiceRequestProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service_request_proposal(
    request_id: str,
    payload: ServiceRequestProposalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    service_request = _get_request_or_404(db, request_id)
    line_items = payload.line_items or []
    subtotal, tax_amount, total = _compute_totals(line_items, payload.tax_rate)

    proposal = ServiceRequestProposal(
        service_request_id=service_request.id,
        created_by_user_id=current_user.id,
        proposal_type=payload.proposal_type,
        title=payload.title,
        introduction=payload.introduction,
        line_items=[item.model_dump() for item in line_items] if line_items else None,
        subtotal=subtotal,
        tax_rate=payload.tax_rate,
        tax_amount=tax_amount,
        total=total if line_items else (payload.budget_amount or 0),
        estimated_days=payload.estimated_days,
        budget_amount=payload.budget_amount,
        currency=payload.currency,
        status="draft",
        public_token=secrets.token_urlsafe(24),
        document_url=payload.document_url,
        notes=payload.notes,
        valid_until=payload.valid_until,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return _serialize_proposal(proposal)


@router.post(
    "/admin/service-requests/{request_id}/proposals/upload",
    response_model=ServiceRequestProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_service_request_proposal(
    request_id: str,
    title: str = Form(...),
    introduction: Optional[str] = Form(None),
    estimated_days: Optional[int] = Form(None),
    budget_amount: Optional[float] = Form(None),
    notes: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    service_request = _get_request_or_404(db, request_id)
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is required")

    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_PROPOSAL_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_PROPOSAL_EXTENSIONS))}",
        )

    PROPOSAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    stored_path = PROPOSAL_UPLOAD_DIR / stored_name
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
    stored_path.write_bytes(content)
    document_url = f"/static/proposals/{stored_name}"

    proposal = ServiceRequestProposal(
        service_request_id=service_request.id,
        created_by_user_id=current_user.id,
        proposal_type="uploaded",
        title=title,
        introduction=introduction,
        line_items=None,
        subtotal=budget_amount or 0,
        tax_rate=0,
        tax_amount=0,
        total=budget_amount or 0,
        estimated_days=estimated_days,
        budget_amount=budget_amount,
        currency="USD",
        status="draft",
        public_token=secrets.token_urlsafe(24),
        document_url=document_url,
        notes=notes,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return _serialize_proposal(proposal)


@router.post("/admin/proposals/{proposal_id}/send", response_model=ServiceRequestProposalResponse)
async def send_service_request_proposal(
    proposal_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    proposal = db.query(ServiceRequestProposal).filter(ServiceRequestProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")

    service_request = _get_request_or_404(db, str(proposal.service_request_id))
    if not service_request.client_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client email is missing")

    proposal.status = "sent"
    proposal.sent_at = datetime.utcnow()
    db.commit()
    db.refresh(proposal)

    background_tasks.add_task(
        notification_service.send_proposal_to_client,
        client_name=service_request.client_name,
        client_email=service_request.client_email,
        service_title=service_request.service_title,
        proposal_title=proposal.title,
        proposal_total=proposal.total,
        currency=proposal.currency,
        estimated_days=proposal.estimated_days,
        public_url=_proposal_public_url(proposal.public_token),
        document_url=proposal.document_url,
    )

    return _serialize_proposal(proposal)


@router.get("/public/proposals/{token}", response_model=ServiceRequestProposalResponse)
async def get_public_proposal(token: str, db: Session = Depends(get_db)) -> Any:
    proposal = db.query(ServiceRequestProposal).filter(ServiceRequestProposal.public_token == token).first()
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return _serialize_proposal(proposal)
