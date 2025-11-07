# app/modules/auth/services/auth_service.py - FIXED
from datetime import timedelta
from typing import Optional
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import AuthenticationException, NotFoundException
from app.core.security import create_access_token
from app.database.session import get_db
from app.modules.auth.models.user import User
from app.modules.auth.repositories.user_repository import UserRepository
from app.modules.auth.schemas.user import TokenPayload, UserCreate, UserUpdate

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


class AuthService:
    def __init__(self):
        self.user_repository = UserRepository()

    def create_user(self, db: Session, user_in: UserCreate) -> User:
        existing_user = self.user_repository.get_by_email(db, email=user_in.email)
        if existing_user:
            raise ValueError("Email already registered")
        
        user_in_data = user_in.model_dump()
        try:
            user = self.user_repository.create(db=db, obj_in=user_in_data)
            return user
        except Exception as e:
            print(f"Error creating user in repository: {str(e)}")
            raise

    def update_user(self, db: Session, user_id: uuid.UUID, user_in: UserUpdate) -> User:
        user = self.user_repository.get_by_id(db, user_id=str(user_id))
        if not user:
            raise NotFoundException("User not found")
        
        user_in_data = user_in.model_dump(exclude_unset=True)
        return self.user_repository.update(db=db, db_obj=user, obj_in=user_in_data)

    def authenticate_user(self, db: Session, email: str, password: str) -> User:
        print(f"🔍 Looking for user with email: {email}")
        user = self.user_repository.authenticate(db=db, email=email, password=password)
        if not user:
            print(f"❌ Authentication failed for: {email}")
            raise AuthenticationException("Incorrect email or password")
        if not user.is_active:
            print(f"❌ User account inactive: {email}")
            raise AuthenticationException("Inactive user account")
        
        print(f"🔍 Found user: {user}")
        print(f"✅ User authenticated successfully")
        return user

    def generate_token(self, user_id: uuid.UUID) -> str:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(
            subject=str(user_id), expires_delta=access_token_expires
        )

    def _get_user_from_token(self, db: Session, token: str) -> User:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            token_data = TokenPayload(**payload)
        except (JWTError, ValidationError) as e:
            print(f"❌ Token validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user = self.user_repository.get_by_id(db, user_id=token_data.sub)
        if not user:
            print(f"❌ User not found for token subject: {token_data.sub}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            print(f"❌ User inactive: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user


# Standalone dependency functions
def get_current_user(
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
) -> User:
    return auth_service._get_user_from_token(db, token)

def get_current_superuser(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    user = auth_service._get_user_from_token(db, token)
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return user

def get_current_active_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    user = auth_service._get_user_from_token(db, token)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    return user

# Create service instance
auth_service = AuthService()

# Make old syntax work by adding functions as attributes
auth_service.get_current_user = get_current_user
auth_service.get_current_superuser = get_current_superuser
auth_service.get_current_active_user = get_current_active_user
