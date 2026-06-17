# app/modules/auth/controllers/auth_controller.py - IMPROVED ERROR HANDLING
from typing import Any
import traceback

from fastapi import APIRouter, Depends, Body, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import get_db
from app.modules.auth.schemas.user import User, UserCreate, Token, UserLogin
from app.modules.auth.services.auth_service import (
    auth_service,
    get_current_user_allow_unverified,
    get_current_superuser,
)
from app.services.email_service import EmailService

router = APIRouter()
email_service = EmailService()


def _send_registration_verification(email: str, user_name: str | None, user_id: str) -> None:
    try:
        email_service.send_verification_email(
            email=email,
            user_name=user_name,
            user_id=user_id,
        )
    except Exception as exc:
        print(f"Failed to send registration verification email: {exc}")


@router.post("/register", response_model=User)
def register(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
) -> Any:
    """Register a new user with improved error handling."""
    try:
        print(f"🔍 Registration attempt for: {user_in.email}")
        print(f"🔍 User data: {user_in.model_dump(exclude={'password'})}")
        
        # Check if user already exists first (outside transaction)
        existing_user = auth_service.user_repository.get_by_email(db, email=user_in.email)
        if existing_user:
            print(f"❌ User already exists: {user_in.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )
        
        # Create the user
        user = auth_service.create_user(db=db, user_in=user_in)
        
        print(f"✅ User created successfully: {user.id}")
        user_name = " ".join(filter(None, [user.first_name, user.last_name])).strip() or None
        background_tasks.add_task(
            _send_registration_verification,
            user.email,
            user_name,
            str(user.id),
        )
        return user
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except ValueError as e:
        print(f"❌ Value error: {str(e)}")
        # Handle known validation errors
        if "Email already registered" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except SQLAlchemyError as e:
        print(f"❌ Database error: {str(e)}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        
        # Rollback the transaction
        try:
            db.rollback()
        except:
            pass
        
        # Check for specific database errors
        error_msg = str(e).lower()
        if "unique" in error_msg and "email" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )
        elif "transaction" in error_msg and "aborted" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database transaction error. Please try again."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred. Please try again."
            )
            
    except Exception as e:
        print(f"❌ Unexpected error in registration: {str(e)}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        
        # Rollback the transaction
        try:
            db.rollback()
        except:
            pass
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """OAuth2 compatible token login with improved error handling."""
    try:
        print(f"🔍 Login attempt for: {form_data.username}")
        
        user = auth_service.authenticate_user(
            db=db, email=form_data.username, password=form_data.password
        )
        
        access_token = auth_service.generate_token(user_id=user.id)
        
        print(f"✅ Login successful for: {form_data.username}")
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        print(f"❌ Database error during login: {str(e)}")
        try:
            db.rollback()
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login service temporarily unavailable"
        )
        
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        try:
            db.rollback()
        except:
            pass
        detail = getattr(e, "detail", None) or str(e) or "Incorrect email or password"
        status_code = getattr(e, "status_code", status.HTTP_401_UNAUTHORIZED)
        raise HTTPException(status_code=status_code, detail=detail)


@router.post("/login/json", response_model=Token)
def login_json(
    db: Session = Depends(get_db),
    login_data: UserLogin = Body(...),
) -> Any:
    """JSON login with improved error handling."""
    try:
        print(f"🔍 JSON login attempt for: {login_data.email}")
        
        user = auth_service.authenticate_user(
            db=db, email=login_data.email, password=login_data.password
        )
        
        access_token = auth_service.generate_token(user_id=user.id)
        
        print(f"✅ JSON login successful for: {login_data.email}")
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        print(f"❌ Database error during JSON login: {str(e)}")
        try:
            db.rollback()
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login service temporarily unavailable"
        )
        
    except Exception as e:
        print(f"❌ JSON login error: {str(e)}")
        try:
            db.rollback()
        except:
            pass
        detail = getattr(e, "detail", None) or str(e) or "Incorrect email or password"
        status_code = getattr(e, "status_code", status.HTTP_401_UNAUTHORIZED)
        raise HTTPException(status_code=status_code, detail=detail)


@router.get("/me", response_model=User)
def read_users_me(
    current_user: User = Depends(get_current_user_allow_unverified),
) -> Any:
    """Get current user."""
    return current_user


@router.get("/users", response_model=list[User])
def get_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """Get all users with improved error handling."""
    try:
        users = auth_service.user_repository.get_all(db=db, skip=skip, limit=limit)
        return users
        
    except SQLAlchemyError as e:
        print(f"❌ Database error getting users: {str(e)}")
        try:
            db.rollback()
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )
        
    except Exception as e:
        print(f"❌ Error getting users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )