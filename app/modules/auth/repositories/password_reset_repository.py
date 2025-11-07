# app/modules/auth/repositories/password_reset_repository.py
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
import secrets

from app.modules.auth.models.password_reset import PasswordResetToken
from app.database.base_class import Base


class PasswordResetRepository:
    """Repository for password reset token operations"""
    
    def create(self, db: Session, user_id: str, expires_in_hours: int = 1) -> Optional[PasswordResetToken]:
        """Create a new password reset token"""
        try:
            # Generate secure token
            token = secrets.token_urlsafe(32)
            
            # Calculate expiration time
            from datetime import timezone
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
            
            # Create token object
            token_obj = PasswordResetToken(
                user_id=user_id,
                token=token,
                expires_at=expires_at
            )
            
            db.add(token_obj)
            db.commit()
            db.refresh(token_obj)
            
            print(f"✅ Password reset token created for user: {user_id}")
            return token_obj
            
        except SQLAlchemyError as e:
            print(f"❌ Database error creating password reset token: {str(e)}")
            db.rollback()
            return None
            
        except Exception as e:
            print(f"❌ Unexpected error creating password reset token: {str(e)}")
            db.rollback()
            return None
    
    def get_by_token(self, db: Session, token: str) -> Optional[PasswordResetToken]:
        """Get password reset token by token string"""
        try:
            return db.query(PasswordResetToken).filter(
                PasswordResetToken.token == token
            ).first()
            
        except SQLAlchemyError as e:
            print(f"❌ Database error getting password reset token: {str(e)}")
            return None
            
        except Exception as e:
            print(f"❌ Unexpected error getting password reset token: {str(e)}")
            return None
    
    def get_by_user_id(self, db: Session, user_id: str) -> List[PasswordResetToken]:
        """Get all password reset tokens for a user"""
        try:
            return db.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == user_id
            ).order_by(PasswordResetToken.created_at.desc()).all()
            
        except SQLAlchemyError as e:
            print(f"❌ Database error getting user password reset tokens: {str(e)}")
            return []
            
        except Exception as e:
            print(f"❌ Unexpected error getting user password reset tokens: {str(e)}")
            return []
    
    def mark_as_used(self, db: Session, token: str) -> bool:
        """Mark a password reset token as used"""
        try:
            token_obj = self.get_by_token(db, token)
            if not token_obj:
                return False
            
            token_obj.is_used = True
            from datetime import timezone
            token_obj.used_at = datetime.now(timezone.utc)
            
            db.commit()
            
            print(f"✅ Password reset token marked as used: {token}")
            return True
            
        except SQLAlchemyError as e:
            print(f"❌ Database error marking password reset token as used: {str(e)}")
            db.rollback()
            return False
            
        except Exception as e:
            print(f"❌ Unexpected error marking password reset token as used: {str(e)}")
            db.rollback()
            return False
    
    def delete_expired_tokens(self, db: Session) -> int:
        """Delete expired password reset tokens"""
        try:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            expired_tokens = db.query(PasswordResetToken).filter(
                PasswordResetToken.expires_at < now
            ).all()
            
            count = len(expired_tokens)
            for token in expired_tokens:
                db.delete(token)
            
            db.commit()
            
            if count > 0:
                print(f"✅ Deleted {count} expired password reset tokens")
            
            return count
            
        except SQLAlchemyError as e:
            print(f"❌ Database error deleting expired tokens: {str(e)}")
            db.rollback()
            return 0
            
        except Exception as e:
            print(f"❌ Unexpected error deleting expired tokens: {str(e)}")
            db.rollback()
            return 0
    
    def delete_user_tokens(self, db: Session, user_id: str) -> bool:
        """Delete all password reset tokens for a user"""
        try:
            user_tokens = db.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == user_id
            ).all()
            
            for token in user_tokens:
                db.delete(token)
            
            db.commit()
            
            print(f"✅ Deleted all password reset tokens for user: {user_id}")
            return True
            
        except SQLAlchemyError as e:
            print(f"❌ Database error deleting user tokens: {str(e)}")
            db.rollback()
            return False
            
        except Exception as e:
            print(f"❌ Unexpected error deleting user tokens: {str(e)}")
            db.rollback()
            return False
