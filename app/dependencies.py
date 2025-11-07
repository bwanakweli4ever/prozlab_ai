from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.models.user import User
from app.modules.auth.services.auth_service import AuthService

auth_service = AuthService()

def get_current_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
) -> User:
    return current_user


def get_current_active_superuser(
    current_user: User = Depends(auth_service.get_current_superuser),
) -> User:
    return current_user
