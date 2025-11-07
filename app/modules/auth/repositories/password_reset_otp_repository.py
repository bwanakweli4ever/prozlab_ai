# app/modules/auth/repositories/password_reset_otp_repository.py
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta, timezone
import secrets
import random

from app.modules.auth.models.otp import OTPVerification
from app.database.base_class import Base


class PasswordResetOTPRepository:
    """Repository for password reset OTP operations"""
    
    def create(self, db: Session, email: str, expires_in_minutes: int = 10) -> Optional[OTPVerification]:
        """Create a new password reset OTP"""
        try:
            # Generate 6-digit OTP
            otp_code = str(random.randint(100000, 999999))
            
            # Calculate expiration time
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
            
            # Create OTP object
            otp_obj = OTPVerification(
                email=email,
                otp_code=otp_code,
                purpose="password_reset",
                expires_at=expires_at
            )
            
            db.add(otp_obj)
            db.commit()
            db.refresh(otp_obj)
            
            print(f"✅ Password reset OTP created for email: {email}")
            return otp_obj
            
        except SQLAlchemyError as e:
            print(f"❌ Database error creating password reset OTP: {str(e)}")
            db.rollback()
            return None
            
        except Exception as e:
            print(f"❌ Unexpected error creating password reset OTP: {str(e)}")
            db.rollback()
            return None
    
    def get_by_email_and_code(self, db: Session, email: str, otp_code: str) -> Optional[OTPVerification]:
        """Get OTP by email and code"""
        try:
            return db.query(OTPVerification).filter(
                OTPVerification.email == email,
                OTPVerification.otp_code == otp_code,
                OTPVerification.purpose == "password_reset"
            ).first()
            
        except SQLAlchemyError as e:
            print(f"❌ Database error getting password reset OTP: {str(e)}")
            return None
    
    def get_latest_by_email(self, db: Session, email: str) -> Optional[OTPVerification]:
        """Get the latest OTP for an email"""
        try:
            return db.query(OTPVerification).filter(
                OTPVerification.email == email,
                OTPVerification.purpose == "password_reset"
            ).order_by(OTPVerification.created_at.desc()).first()
            
        except SQLAlchemyError as e:
            print(f"❌ Database error getting latest password reset OTP: {str(e)}")
            return None
    
    def mark_as_verified(self, db: Session, email: str, otp_code: str) -> bool:
        """Mark OTP as verified"""
        try:
            otp_obj = self.get_by_email_and_code(db, email, otp_code)
            if not otp_obj:
                return False
            
            otp_obj.is_verified = True
            otp_obj.verified_at = datetime.now(timezone.utc)
            db.commit()
            
            print(f"✅ Password reset OTP marked as verified for email: {email}")
            return True
            
        except SQLAlchemyError as e:
            print(f"❌ Database error marking password reset OTP as verified: {str(e)}")
            db.rollback()
            return False
    
    def increment_attempts(self, db: Session, email: str, otp_code: str) -> bool:
        """Increment OTP attempts"""
        try:
            otp_obj = self.get_by_email_and_code(db, email, otp_code)
            if not otp_obj:
                return False
            
            otp_obj.attempts += 1
            db.commit()
            
            print(f"✅ Password reset OTP attempts incremented for email: {email}")
            return True
            
        except SQLAlchemyError as e:
            print(f"❌ Database error incrementing password reset OTP attempts: {str(e)}")
            db.rollback()
            return False
    
    def delete_expired_otps(self, db: Session) -> int:
        """Delete expired OTPs"""
        try:
            now = datetime.now(timezone.utc)
            expired_otps = db.query(OTPVerification).filter(
                OTPVerification.expires_at < now,
                OTPVerification.purpose == "password_reset"
            ).all()
            
            count = len(expired_otps)
            for otp in expired_otps:
                db.delete(otp)
            
            db.commit()
            
            if count > 0:
                print(f"✅ Deleted {count} expired password reset OTPs")
            
            return count
            
        except SQLAlchemyError as e:
            print(f"❌ Database error deleting expired password reset OTPs: {str(e)}")
            db.rollback()
            return 0
    
    def delete_otps_for_email(self, db: Session, email: str) -> int:
        """Delete all OTPs for a specific email"""
        try:
            otps = db.query(OTPVerification).filter(
                OTPVerification.email == email,
                OTPVerification.purpose == "password_reset"
            ).all()
            
            count = len(otps)
            for otp in otps:
                db.delete(otp)
            
            db.commit()
            
            if count > 0:
                print(f"✅ Deleted {count} password reset OTPs for email: {email}")
            
            return count
            
        except SQLAlchemyError as e:
            print(f"❌ Database error deleting password reset OTPs for email: {str(e)}")
            db.rollback()
            return 0
    
    def get_attempts_count(self, db: Session, email: str, otp_code: str) -> int:
        """Get current attempts count for an OTP"""
        try:
            otp_obj = self.get_by_email_and_code(db, email, otp_code)
            return otp_obj.attempts if otp_obj else 0
            
        except SQLAlchemyError as e:
            print(f"❌ Database error getting password reset OTP attempts: {str(e)}")
            return 0
