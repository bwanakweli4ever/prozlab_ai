# app/modules/auth/repositories/user_repository.py - FIXED WITH PROPER ERROR HANDLING
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import uuid

from app.core.security import get_password_hash, verify_password
from app.modules.auth.models.user import User
from app.modules.auth.schemas.user import UserCreate, UserUpdate


class UserRepository:
    """User repository with proper transaction handling"""
    
    def get_by_id(self, db: Session, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            return db.query(User).filter(User.id == user_id).first()
        except SQLAlchemyError as e:
            print(f"❌ Error getting user by ID {user_id}: {str(e)}")
            db.rollback()
            return None
    
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            return db.query(User).filter(User.email == email).first()
        except SQLAlchemyError as e:
            print(f"❌ Error getting user by email {email}: {str(e)}")
            db.rollback()
            return None
    
    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        try:
            return db.query(User).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            print(f"❌ Error getting users: {str(e)}")
            db.rollback()
            return []
    
    def create(self, db: Session, obj_in: dict) -> Optional[User]:
        """Create a new user with proper transaction handling"""
        try:
            print(f"🔍 Creating user with data: {obj_in}")
            
            # Create user object
            db_user = User(
                id=str(uuid.uuid4()),
                email=obj_in["email"],
                first_name=obj_in.get("first_name", ""),
                last_name=obj_in.get("last_name", ""),
                hashed_password=get_password_hash(obj_in["password"]),
                is_active=obj_in.get("is_active", True),
                is_superuser=obj_in.get("is_superuser", False),
                is_verified=obj_in.get("is_verified", False)
            )
            
            print(f"🔍 User object created: {db_user.email}")
            
            # Add to session
            db.add(db_user)
            
            # Commit the transaction
            db.commit()
            
            # Refresh to get the created_at and updated_at values
            db.refresh(db_user)
            
            print(f"✅ User created successfully: {db_user.id}")
            return db_user
            
        except IntegrityError as e:
            print(f"❌ Integrity error creating user: {str(e)}")
            db.rollback()
            
            # Check if it's a duplicate email error
            if "email" in str(e).lower() and "unique" in str(e).lower():
                raise ValueError("Email already registered")
            else:
                raise ValueError(f"Database constraint violation: {str(e)}")
                
        except SQLAlchemyError as e:
            print(f"❌ Database error creating user: {str(e)}")
            db.rollback()
            raise Exception(f"Failed to create user: {str(e)}")
            
        except Exception as e:
            print(f"❌ Unexpected error creating user: {str(e)}")
            db.rollback()
            raise Exception(f"Unexpected error: {str(e)}")
    
    def update(self, db: Session, db_obj: User, obj_in: dict) -> Optional[User]:
        """Update user with proper transaction handling"""
        try:
            print(f"🔍 Updating user {db_obj.id} with data: {obj_in}")
            
            # Update fields
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    if field == "password":
                        setattr(db_obj, "hashed_password", get_password_hash(value))
                    else:
                        setattr(db_obj, field, value)
            
            # Commit the transaction
            db.commit()
            
            # Refresh the object
            db.refresh(db_obj)
            
            print(f"✅ User updated successfully: {db_obj.id}")
            return db_obj
            
        except IntegrityError as e:
            print(f"❌ Integrity error updating user: {str(e)}")
            db.rollback()
            raise ValueError(f"Database constraint violation: {str(e)}")
            
        except SQLAlchemyError as e:
            print(f"❌ Database error updating user: {str(e)}")
            db.rollback()
            raise Exception(f"Failed to update user: {str(e)}")
            
        except Exception as e:
            print(f"❌ Unexpected error updating user: {str(e)}")
            db.rollback()
            raise Exception(f"Unexpected error: {str(e)}")
    
    def delete(self, db: Session, user_id: str) -> bool:
        """Delete user with proper transaction handling"""
        try:
            user = self.get_by_id(db, user_id)
            if not user:
                return False
            
            db.delete(user)
            db.commit()
            
            print(f"✅ User deleted successfully: {user_id}")
            return True
            
        except SQLAlchemyError as e:
            print(f"❌ Database error deleting user: {str(e)}")
            db.rollback()
            return False
            
        except Exception as e:
            print(f"❌ Unexpected error deleting user: {str(e)}")
            db.rollback()
            return False
    
    def authenticate(self, db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with proper error handling"""
        try:
            user = self.get_by_email(db, email)
            if not user:
                print(f"❌ User not found: {email}")
                return None
            
            if not verify_password(password, user.hashed_password):
                print(f"❌ Invalid password for user: {email}")
                return None
            
            print(f"✅ User authenticated: {email}")
            return user
            
        except SQLAlchemyError as e:
            print(f"❌ Database error during authentication: {str(e)}")
            db.rollback()
            return None
            
        except Exception as e:
            print(f"❌ Unexpected error during authentication: {str(e)}")
            return None