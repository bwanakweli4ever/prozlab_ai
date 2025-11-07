# app/services/notification_service.py
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.services.email_service import EmailService
from app.config.settings import settings

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
        
        subject = f"New Task Assignment: {service_title}"
        
        # Create assignment details
        assignment_details = f"""
        <h3>Assignment Details:</h3>
        <ul>
            <li><strong>Service:</strong> {service_title}</li>
            <li><strong>Company:</strong> {company_name}</li>
            <li><strong>Client:</strong> {client_name}</li>
        """
        
        if due_date:
            assignment_details += f'<li><strong>Due Date:</strong> {due_date}</li>'
        if estimated_hours:
            assignment_details += f'<li><strong>Estimated Hours:</strong> {estimated_hours}</li>'
        if proposed_rate:
            assignment_details += f'<li><strong>Proposed Rate:</strong> ${proposed_rate}/hour</li>'
        
        assignment_details += "</ul>"
        
        if assignment_notes:
            assignment_details += f"<h4>Special Instructions:</h4><p>{assignment_notes}</p>"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>New Task Assignment</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; background-color: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 10px 5px; }}
                .button.reject {{ background-color: #f44336; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
                .service-description {{ background-color: #fff; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎯 New Task Assignment</h1>
            </div>
            <div class="content">
                <h2>Hello {professional_name}!</h2>
                <p>You have been assigned a new task. Please review the details below and respond accordingly.</p>
                
                {assignment_details}
                
                <div class="service-description">
                    <h4>Service Description:</h4>
                    <p>{service_description}</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://localhost:3001/professional/tasks" class="button">View in Dashboard</a>
                    <a href="http://localhost:3001/professional/tasks" class="button reject">Decline Task</a>
                </div>
                
                <p><strong>Please respond within 24 hours to accept or decline this assignment.</strong></p>
                
                <p>If you have any questions, please contact our support team.</p>
            </div>
            <div class="footer">
                <p>This email was sent from {settings.PROJECT_NAME}</p>
                <p>Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        New Task Assignment
        
        Hello {professional_name}!
        
        You have been assigned a new task. Please review the details below and respond accordingly.
        
        Assignment Details:
        - Service: {service_title}
        - Company: {company_name}
        - Client: {client_name}
        """
        
        if due_date:
            text_body += f"- Due Date: {due_date}\n"
        if estimated_hours:
            text_body += f"- Estimated Hours: {estimated_hours}\n"
        if proposed_rate:
            text_body += f"- Proposed Rate: ${proposed_rate}/hour\n"
        
        text_body += f"""
        
        Service Description:
        {service_description}
        
        Please respond within 24 hours to accept or decline this assignment.
        
        View in Dashboard: http://localhost:3001/professional/tasks
        
        If you have any questions, please contact our support team.
        
        Best regards,
        The {settings.PROJECT_NAME} Team
        """
        
        return subject, html_body, text_body
    
    def _create_task_accepted_email(self, admin_name: str, admin_email: str, professional_name: str,
                                  service_title: str, company_name: str, client_name: str,
                                  accepted_at: str) -> tuple:
        """Create task accepted notification email for admin"""
        
        subject = f"Task Accepted: {service_title} by {professional_name}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Task Accepted</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; background-color: #2196F3; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
                .success {{ color: #4CAF50; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>✅ Task Accepted</h1>
            </div>
            <div class="content">
                <h2>Great News!</h2>
                <p>Hello {admin_name},</p>
                <p class="success">The task has been accepted by the assigned professional!</p>
                
                <h3>Task Details:</h3>
                <ul>
                    <li><strong>Service:</strong> {service_title}</li>
                    <li><strong>Company:</strong> {company_name}</li>
                    <li><strong>Client:</strong> {client_name}</li>
                    <li><strong>Professional:</strong> {professional_name}</li>
                    <li><strong>Accepted At:</strong> {accepted_at}</li>
                </ul>
                
                <div style="text-align: center;">
                    <a href="http://localhost:3000/admin/tasks" class="button">View in Admin Dashboard</a>
                </div>
                
                <p>The professional will now begin working on the task. You can track progress through the admin dashboard.</p>
            </div>
            <div class="footer">
                <p>This email was sent from {settings.PROJECT_NAME}</p>
                <p>Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Task Accepted
        
        Hello {admin_name},
        
        Great news! The task has been accepted by the assigned professional.
        
        Task Details:
        - Service: {service_title}
        - Company: {company_name}
        - Client: {client_name}
        - Professional: {professional_name}
        - Accepted At: {accepted_at}
        
        The professional will now begin working on the task. You can track progress through the admin dashboard.
        
        View in Admin Dashboard: http://localhost:3000/admin/tasks
        
        Best regards,
        The {settings.PROJECT_NAME} Team
        """
        
        return subject, html_body, text_body
    
    def _create_task_rejected_email(self, admin_name: str, admin_email: str, professional_name: str,
                                  service_title: str, company_name: str, client_name: str,
                                  rejection_reason: str = None) -> tuple:
        """Create task rejected notification email for admin"""
        
        subject = f"Task Declined: {service_title} by {professional_name}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Task Declined</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; background-color: #2196F3; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
                .warning {{ color: #f44336; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>❌ Task Declined</h1>
            </div>
            <div class="content">
                <h2>Task Assignment Update</h2>
                <p>Hello {admin_name},</p>
                <p class="warning">The assigned professional has declined the task.</p>
                
                <h3>Task Details:</h3>
                <ul>
                    <li><strong>Service:</strong> {service_title}</li>
                    <li><strong>Company:</strong> {company_name}</li>
                    <li><strong>Client:</strong> {client_name}</li>
                    <li><strong>Professional:</strong> {professional_name}</li>
                </ul>
                
                {f'<h4>Reason for Decline:</h4><p>{rejection_reason}</p>' if rejection_reason else ''}
                
                <div style="text-align: center;">
                    <a href="http://localhost:3000/admin/tasks" class="button">Assign to Another Professional</a>
                </div>
                
                <p>You may want to assign this task to another qualified professional or contact the client for more details.</p>
            </div>
            <div class="footer">
                <p>This email was sent from {settings.PROJECT_NAME}</p>
                <p>Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Task Declined
        
        Hello {admin_name},
        
        The assigned professional has declined the task.
        
        Task Details:
        - Service: {service_title}
        - Company: {company_name}
        - Client: {client_name}
        - Professional: {professional_name}
        
        {f'Reason for Decline: {rejection_reason}' if rejection_reason else ''}
        
        You may want to assign this task to another qualified professional or contact the client for more details.
        
        Assign to Another Professional: http://localhost:3000/admin/tasks
        
        Best regards,
        The {settings.PROJECT_NAME} Team
        """
        
        return subject, html_body, text_body
    
    def _create_service_request_received_email(self, admin_name: str, admin_email: str,
                                             company_name: str, client_name: str, client_email: str,
                                             service_title: str, service_description: str,
                                             priority: str, created_at: str) -> tuple:
        """Create service request received notification email for admin"""
        
        subject = f"New Service Request: {service_title} from {company_name}"
        
        # Priority color coding
        priority_colors = {
            "LOW": "#4CAF50",
            "MEDIUM": "#FF9800", 
            "HIGH": "#f44336",
            "URGENT": "#9C27B0"
        }
        priority_color = priority_colors.get(priority, "#2196F3")
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>New Service Request</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; background-color: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
                .priority {{ display: inline-block; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold; }}
                .service-description {{ background-color: #fff; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📋 New Service Request</h1>
            </div>
            <div class="content">
                <h2>Hello {admin_name}!</h2>
                <p>A new service request has been submitted and requires your attention.</p>
                
                <h3>Request Details:</h3>
                <ul>
                    <li><strong>Service:</strong> {service_title}</li>
                    <li><strong>Company:</strong> {company_name}</li>
                    <li><strong>Client:</strong> {client_name}</li>
                    <li><strong>Client Email:</strong> {client_email}</li>
                    <li><strong>Priority:</strong> <span class="priority" style="background-color: {priority_color};">{priority}</span></li>
                    <li><strong>Submitted:</strong> {created_at}</li>
                </ul>
                
                <div class="service-description">
                    <h4>Service Description:</h4>
                    <p>{service_description}</p>
                </div>
                
                <div style="text-align: center;">
                    <a href="http://localhost:3000/admin/service-requests" class="button">Review Request</a>
                </div>
                
                <p>Please review this request and assign it to an appropriate professional as soon as possible.</p>
            </div>
            <div class="footer">
                <p>This email was sent from {settings.PROJECT_NAME}</p>
                <p>Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        New Service Request
        
        Hello {admin_name}!
        
        A new service request has been submitted and requires your attention.
        
        Request Details:
        - Service: {service_title}
        - Company: {company_name}
        - Client: {client_name}
        - Client Email: {client_email}
        - Priority: {priority}
        - Submitted: {created_at}
        
        Service Description:
        {service_description}
        
        Please review this request and assign it to an appropriate professional as soon as possible.
        
        Review Request: http://localhost:3000/admin/service-requests
        
        Best regards,
        The {settings.PROJECT_NAME} Team
        """
        
        return subject, html_body, text_body
    
    def _create_verification_email(self, user_name: str, verification_url: str) -> tuple:
        """Create email verification email"""
        subject = f"Verify your email for {settings.PROJECT_NAME}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Email Verification</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; background-color: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>✅ Email Verification</h1>
            </div>
            <div class="content">
                <h2>Hello {user_name}!</h2>
                <p>Thank you for signing up! Please verify your email address to complete your registration.</p>
                
                <div style="text-align: center;">
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                </div>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background-color: #fff; padding: 10px; border-radius: 3px;">
                    {verification_url}
                </p>
                
                <p><strong>This verification link will expire in 24 hours.</strong></p>
            </div>
            <div class="footer">
                <p>This email was sent from {settings.PROJECT_NAME}</p>
                <p>Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Email Verification
        
        Hello {user_name}!
        
        Thank you for signing up! Please verify your email address to complete your registration.
        
        Verification Link: {verification_url}
        
        This verification link will expire in 24 hours.
        
        Best regards,
        The {settings.PROJECT_NAME} Team
        """
        
        return subject, html_body, text_body
    
    def _create_password_reset_email(self, user_name: str, reset_url: str) -> tuple:
        """Create password reset email"""
        subject = "Reset Your Password"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Password Reset</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; background-color: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
                .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔒 Password Reset Request</h1>
            </div>
            <div class="content">
                <h2>Hello {user_name}!</h2>
                <p>We received a request to reset your password. Click the button below to reset it:</p>
                
                <div style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </div>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background-color: #fff; padding: 10px; border-radius: 3px;">
                    {reset_url}
                </p>
                
                <div class="warning">
                    <strong>Important:</strong>
                    <ul>
                        <li>This link will expire in 1 hour</li>
                        <li>If you didn't request this password reset, please ignore this email</li>
                        <li>Your password will remain unchanged until you create a new one</li>
                    </ul>
                </div>
            </div>
            <div class="footer">
                <p>This email was sent from {settings.PROJECT_NAME}</p>
                <p>Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Password Reset Request
        
        Hello {user_name}!
        
        We received a request to reset your password. Please visit this link to reset it:
        {reset_url}
        
        Important:
        - This link will expire in 1 hour
        - If you didn't request this password reset, please ignore this email
        - Your password will remain unchanged until you create a new one
        
        Best regards,
        The {settings.PROJECT_NAME} Team
        """
        
        return subject, html_body, text_body
    
    def _create_profile_verification_email(self, user_name: str, is_approved: Optional[bool] = None,
                                         admin_notes: Optional[str] = None, rejection_reason: Optional[str] = None,
                                         new_status: Optional[str] = None, old_status: Optional[str] = None) -> tuple:
        """Create profile verification status change email"""
        from app.config.settings import settings
        
        if is_approved is True:
            subject = f"🎉 Your Professional Profile Has Been Verified - {settings.PROJECT_NAME}"
            status_message = "Your professional profile has been successfully verified!"
            color = "#4CAF50"
            next_steps = "You can now start accepting task assignments and building your reputation on our platform."
        elif is_approved is False:
            subject = f"Profile Verification Update - {settings.PROJECT_NAME}"
            status_message = "Your professional profile requires additional review."
            color = "#FF9800"
            next_steps = "Please review the feedback below and update your profile accordingly. You can resubmit for verification once you've made the necessary changes."
        else:
            subject = f"Profile Status Update - {settings.PROJECT_NAME}"
            status_message = f"Your profile status has been updated from '{old_status}' to '{new_status}'."
            color = "#2196F3"
            next_steps = "Please check your dashboard for any additional requirements."
        
        # Create HTML body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Profile Verification Update</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .status-box {{ background-color: #fff; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid {color}; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: {color}; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .admin-notes {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .warning {{ background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 15px 0; color: #721c24; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Profile Verification Update</h1>
            </div>
            <div class="content">
                <h2>Hello {user_name}!</h2>
                
                <div class="status-box">
                    <h3>{status_message}</h3>
                    <p>{next_steps}</p>
                </div>
        """
        
        if admin_notes:
            html_body += f"""
                <div class="admin-notes">
                    <h4>Administrative Notes:</h4>
                    <p>{admin_notes}</p>
                </div>
            """
        
        if rejection_reason:
            html_body += f"""
                <div class="warning">
                    <h4>Reason for Review:</h4>
                    <p>{rejection_reason}</p>
                </div>
            """
        
        html_body += f"""
                <p>
                    <a href="http://localhost:3001/dashboard" class="button">View Your Dashboard</a>
                </p>
                
                <p>If you have any questions, please contact our support team at {settings.MAIL_SUPPORT or 'support@prozlab.com'}.</p>
                
                <p>Best regards,<br>The {settings.PROJECT_NAME} Team</p>
            </div>
            <div class="footer">
                <p>This email was sent from {settings.PROJECT_NAME}</p>
                <p>Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        # Create text body
        text_body = f"""
        Profile Verification Update
        
        Hello {user_name}!
        
        {status_message}
        
        {next_steps}
        """
        
        if admin_notes:
            text_body += f"""
        
        Administrative Notes:
        {admin_notes}
        """
        
        if rejection_reason:
            text_body += f"""
        
        Reason for Review:
        {rejection_reason}
        """
        
        text_body += f"""
        
        View your dashboard: http://localhost:3001/dashboard
        
        If you have any questions, please contact our support team at {settings.MAIL_SUPPORT or 'support@prozlab.com'}.
        
        Best regards,
        The {settings.PROJECT_NAME} Team
        """
        
        return subject, html_body, text_body
    
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
                self.email_service._send_smtp_email(to_email, subject, html_body, text_body)
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
