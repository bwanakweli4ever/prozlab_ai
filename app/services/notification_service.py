# app/services/notification_service.py
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.services.email_service import EmailService
from app.config.settings import settings
from app.services.email_templates import (
    build_password_reset_email,
    build_profile_status_email,
    build_simple_notification_email,
    build_verification_email,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending various types of email notifications"""
    
    def __init__(self):
        self.email_service = EmailService()
    
    def _create_email_template(self, template_type: str, **kwargs) -> tuple:
        """Create email templates for different notification types"""
        
        if template_type == "task_assignment":
            return self._create_task_assignment_email(**kwargs)
        elif template_type == "task_accepted":
            return self._create_task_accepted_email(**kwargs)
        elif template_type == "task_rejected":
            return self._create_task_rejected_email(**kwargs)
        elif template_type == "service_request_received":
            return self._create_service_request_received_email(**kwargs)
        elif template_type == "email_verification":
            return self._create_verification_email(**kwargs)
        elif template_type == "password_reset":
            return self._create_password_reset_email(**kwargs)
        elif template_type == "profile_verification":
            return self._create_profile_verification_email(**kwargs)
        else:
            raise ValueError(f"Unknown template type: {template_type}")
    
    def _create_task_assignment_email(self, professional_name: str, professional_email: str, 
                                    service_title: str, company_name: str, client_name: str,
                                    service_description: str, assignment_notes: str = None,
                                    due_date: str = None, estimated_hours: float = None,
                                    proposed_rate: float = None) -> tuple:
        """Create task assignment email for professional"""
        app_url = settings.APP_URL.rstrip("/")
        details = [
            f"<li><strong>Service:</strong> {service_title}</li>",
            f"<li><strong>Company:</strong> {company_name}</li>",
            f"<li><strong>Client:</strong> {client_name}</li>",
        ]
        if due_date:
            details.append(f"<li><strong>Due Date:</strong> {due_date}</li>")
        if estimated_hours:
            details.append(f"<li><strong>Estimated Hours:</strong> {estimated_hours}</li>")
        if proposed_rate:
            details.append(f"<li><strong>Proposed Rate:</strong> ${proposed_rate}/hour</li>")
        notes_html = (
            f"<p style='margin-top:12px;'><strong>Special instructions:</strong><br/>{assignment_notes}</p>"
            if assignment_notes
            else ""
        )
        body_html = (
            "<p>You have been assigned a new task. Please review the details below and respond accordingly.</p>"
            f"<ul style='padding-left:18px;'>{''.join(details)}</ul>"
            f"<div style='margin:16px 0;padding:14px 16px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;'>"
            f"<strong>Service description</strong><p style='margin:8px 0 0;'>{service_description}</p></div>"
            f"{notes_html}"
            "<p><strong>Please respond within 24 hours to accept or decline this assignment.</strong></p>"
        )
        return build_simple_notification_email(
            subject=f"New Task Assignment: {service_title}",
            title="New Task Assignment",
            greeting_name=professional_name,
            body_html=body_html,
            cta_label="View in Dashboard",
            cta_url=f"{app_url}/dashboard",
            hero="bell",
        )
    
    def _create_task_accepted_email(self, admin_name: str, admin_email: str, professional_name: str,
                                  service_title: str, company_name: str, client_name: str,
                                  accepted_at: str) -> tuple:
        """Create task accepted notification email for admin"""
        app_url = settings.APP_URL.rstrip("/")
        body_html = (
            "<p><strong style='color:#2EAD5C;'>The task has been accepted by the assigned professional!</strong></p>"
            "<ul style='padding-left:18px;'>"
            f"<li><strong>Service:</strong> {service_title}</li>"
            f"<li><strong>Company:</strong> {company_name}</li>"
            f"<li><strong>Client:</strong> {client_name}</li>"
            f"<li><strong>Professional:</strong> {professional_name}</li>"
            f"<li><strong>Accepted at:</strong> {accepted_at}</li>"
            "</ul>"
            "<p>The professional will now begin working on the task. You can track progress through the admin dashboard.</p>"
        )
        return build_simple_notification_email(
            subject=f"Task Accepted: {service_title} by {professional_name}",
            title="Task Accepted",
            greeting_name=admin_name,
            body_html=body_html,
            cta_label="View in Admin Dashboard",
            cta_url=f"{app_url}/admin",
            hero="check",
        )
    
    def _create_task_rejected_email(self, admin_name: str, admin_email: str, professional_name: str,
                                  service_title: str, company_name: str, client_name: str,
                                  rejection_reason: str = None) -> tuple:
        """Create task rejected notification email for admin"""
        app_url = settings.APP_URL.rstrip("/")
        reason_html = (
            f"<p style='margin-top:12px;'><strong>Reason for decline:</strong><br/>{rejection_reason}</p>"
            if rejection_reason
            else ""
        )
        body_html = (
            "<p><strong style='color:#DC2626;'>The assigned professional has declined the task.</strong></p>"
            "<ul style='padding-left:18px;'>"
            f"<li><strong>Service:</strong> {service_title}</li>"
            f"<li><strong>Company:</strong> {company_name}</li>"
            f"<li><strong>Client:</strong> {client_name}</li>"
            f"<li><strong>Professional:</strong> {professional_name}</li>"
            "</ul>"
            f"{reason_html}"
            "<p>You may want to assign this task to another qualified professional or contact the client for more details.</p>"
        )
        return build_simple_notification_email(
            subject=f"Task Declined: {service_title} by {professional_name}",
            title="Task Declined",
            greeting_name=admin_name,
            body_html=body_html,
            cta_label="Assign to Another Professional",
            cta_url=f"{app_url}/admin",
            hero="bell",
        )
    
    def _create_service_request_received_email(self, admin_name: str, admin_email: str,
                                             company_name: str, client_name: str, client_email: str,
                                             service_title: str, service_description: str,
                                             priority: str, created_at: str) -> tuple:
        """Create service request received notification email for admin"""
        app_url = settings.APP_URL.rstrip("/")
        body_html = (
            "<p>A new service request has been submitted and requires your attention.</p>"
            "<ul style='padding-left:18px;'>"
            f"<li><strong>Service:</strong> {service_title}</li>"
            f"<li><strong>Company:</strong> {company_name}</li>"
            f"<li><strong>Client:</strong> {client_name}</li>"
            f"<li><strong>Client email:</strong> {client_email}</li>"
            f"<li><strong>Priority:</strong> {priority}</li>"
            f"<li><strong>Submitted:</strong> {created_at}</li>"
            "</ul>"
            f"<div style='margin:16px 0;padding:14px 16px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;'>"
            f"<strong>Service description</strong><p style='margin:8px 0 0;'>{service_description}</p></div>"
            "<p>Please review this request and assign it to an appropriate professional as soon as possible.</p>"
        )
        return build_simple_notification_email(
            subject=f"New Service Request: {service_title} from {company_name}",
            title="New Service Request",
            greeting_name=admin_name,
            body_html=body_html,
            cta_label="Review Request",
            cta_url=f"{app_url}/admin",
            hero="bell",
        )

    def _create_verification_email(self, user_name: str, verification_url: str) -> tuple:
        """Create email verification email"""
        return build_verification_email(
            email="",
            token="",
            user_name=user_name,
            verification_url=verification_url,
        )

    def _create_password_reset_email(self, user_name: str, reset_url: str) -> tuple:
        """Create password reset email"""
        return build_password_reset_email(user_name, reset_url)
    
    def _create_profile_verification_email(self, user_name: str, is_approved: Optional[bool] = None,
                                         admin_notes: Optional[str] = None, rejection_reason: Optional[str] = None,
                                         new_status: Optional[str] = None, old_status: Optional[str] = None) -> tuple:
        """Create profile verification status change email"""
        if is_approved is True:
            subject = f"Your Professional Profile Has Been Verified - {settings.PROJECT_NAME}"
            status_message = "Your professional profile has been successfully verified!"
            next_steps = "You can now start accepting task assignments and building your reputation on our platform."
            hero = "check"
        elif is_approved is False:
            subject = f"Profile Verification Update - {settings.PROJECT_NAME}"
            status_message = "Your professional profile requires additional review."
            next_steps = "Please review the feedback below and update your profile accordingly. You can resubmit for verification once you've made the necessary changes."
            hero = "bell"
        else:
            subject = f"Profile Status Update - {settings.PROJECT_NAME}"
            status_message = f"Your profile status has been updated from '{old_status}' to '{new_status}'."
            next_steps = "Please check your dashboard for any additional requirements."
            hero = "bell"

        return build_profile_status_email(
            user_name,
            subject=subject,
            status_message=status_message,
            next_steps=next_steps,
            admin_notes=admin_notes,
            rejection_reason=rejection_reason,
            hero=hero,
        )
    
    def send_notification(self, template_type: str, to_email: str, to_name: str = None, **kwargs) -> Dict[str, Any]:
        """Send notification email"""
        try:
            # Create email content
            subject, html_body, text_body = self._create_email_template(template_type, **kwargs)
            
            if self.email_service.development_mode:
                # Development mode - log email details
                logger.info(f"📧 DEVELOPMENT MODE - {template_type} email to {to_email}")
                logger.info(f"📧 Subject: {subject}")
                print(f"📧 DEVELOPMENT MODE - {template_type} email to {to_email}")
                print(f"📧 Subject: {subject}")
                
                return {
                    "success": True,
                    "message": f"{template_type} email sent (development mode)",
                    "development_mode": True,
                    "template_type": template_type,
                    "to_email": to_email
                }
            else:
                # Production mode - send actual email
                self.email_service.send_email(
                    to_email=to_email,
                    subject=subject,
                    html_body=html_body,
                    text_body=text_body,
                    to_name=to_name or to_email,
                )
                logger.info(f"✅ {template_type} email sent to {to_email}")
                
                return {
                    "success": True,
                    "message": f"{template_type} email sent successfully",
                    "development_mode": False,
                    "template_type": template_type,
                    "to_email": to_email
                }
                
        except Exception as e:
            logger.error(f"Error sending {template_type} email to {to_email}: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to send {template_type} email",
                "error_code": "EMAIL_SEND_FAILED",
                "error_details": str(e),
                "template_type": template_type,
                "to_email": to_email
            }
    
    def send_task_assignment_notification(self, professional_email: str, professional_name: str,
                                        service_title: str, company_name: str, client_name: str,
                                        service_description: str, assignment_notes: str = None,
                                        due_date: str = None, estimated_hours: float = None,
                                        proposed_rate: float = None) -> Dict[str, Any]:
        """Send task assignment notification to professional"""
        return self.send_notification(
            template_type="task_assignment",
            to_email=professional_email,
            to_name=professional_name,
            professional_name=professional_name,
            professional_email=professional_email,
            service_title=service_title,
            company_name=company_name,
            client_name=client_name,
            service_description=service_description,
            assignment_notes=assignment_notes,
            due_date=due_date,
            estimated_hours=estimated_hours,
            proposed_rate=proposed_rate
        )
    
    def send_task_accepted_notification(self, admin_email: str, admin_name: str, professional_name: str,
                                      service_title: str, company_name: str, client_name: str,
                                      accepted_at: str) -> Dict[str, Any]:
        """Send task accepted notification to admin"""
        return self.send_notification(
            template_type="task_accepted",
            to_email=admin_email,
            to_name=admin_name,
            admin_name=admin_name,
            admin_email=admin_email,
            professional_name=professional_name,
            service_title=service_title,
            company_name=company_name,
            client_name=client_name,
            accepted_at=accepted_at
        )
    
    def send_task_rejected_notification(self, admin_email: str, admin_name: str, professional_name: str,
                                      service_title: str, company_name: str, client_name: str,
                                      rejection_reason: str = None) -> Dict[str, Any]:
        """Send task rejected notification to admin"""
        return self.send_notification(
            template_type="task_rejected",
            to_email=admin_email,
            to_name=admin_name,
            admin_name=admin_name,
            admin_email=admin_email,
            professional_name=professional_name,
            service_title=service_title,
            company_name=company_name,
            client_name=client_name,
            rejection_reason=rejection_reason
        )
    
    def send_service_request_notification(self, admin_email: str, admin_name: str,
                                        company_name: str, client_name: str, client_email: str,
                                        service_title: str, service_description: str,
                                        priority: str, created_at: str) -> Dict[str, Any]:
        """Send service request received notification to admin"""
        return self.send_notification(
            template_type="service_request_received",
            to_email=admin_email,
            to_name=admin_name,
            admin_name=admin_name,
            admin_email=admin_email,
            company_name=company_name,
            client_name=client_name,
            client_email=client_email,
            service_title=service_title,
            service_description=service_description,
            priority=priority,
            created_at=created_at
        )
    
    def send_verification_notification(self, user_email: str, user_name: str, verification_url: str) -> Dict[str, Any]:
        """Send email verification notification"""
        return self.send_notification(
            template_type="email_verification",
            to_email=user_email,
            to_name=user_name,
            user_name=user_name,
            verification_url=verification_url
        )
    
    def send_password_reset_notification(self, user_email: str, user_name: str, reset_url: str) -> Dict[str, Any]:
        """Send password reset notification"""
        return self.send_notification(
            template_type="password_reset",
            to_email=user_email,
            to_name=user_name,
            user_name=user_name,
            reset_url=reset_url
        )
    
    def send_profile_verification_notification(
        self, 
        user_email: str, 
        user_name: str, 
        is_approved: Optional[bool] = None,
        admin_notes: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        new_status: Optional[str] = None,
        old_status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send profile verification status change notification"""
        return self.send_notification(
            template_type="profile_verification",
            to_email=user_email,
            to_name=user_name,
            user_name=user_name,
            is_approved=is_approved,
            admin_notes=admin_notes,
            rejection_reason=rejection_reason,
            new_status=new_status,
            old_status=old_status
        )
