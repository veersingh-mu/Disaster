"""FastAPI route dependencies for authentication and authorization."""

import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.jwt import decode_access_token
from backend.app.database import get_db
from backend.app.models.enums import UserRole
from backend.app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception from None

    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        user = db.execute(select(User).where(User.id == str(user_id))).scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return user


def require_analyst(current_user: User = Depends(get_current_user)) -> User:
    """Enforce that the authenticated user has the 'analyst' role."""
    if current_user.role != UserRole.ANALYST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires analyst role",
        )
    return current_user


def get_user_scenario(
    scenario_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve scenario and enforce row-level ownership (user_id == current_user.id)."""
    from backend.app.errors import ForbiddenError, NotFoundError
    from backend.app.models.scenario import Scenario

    scenario = db.execute(select(Scenario).where(Scenario.id == scenario_id)).scalar_one_or_none()
    if scenario is None:
        raise NotFoundError(
            message=f"Scenario with ID '{scenario_id}' was not found",
            error_code="SCENARIO_NOT_FOUND",
        )

    if scenario.user_id != current_user.id:
        raise ForbiddenError(
            message="You do not have permission to access this scenario",
            error_code="FORBIDDEN_SCENARIO_ACCESS",
        )

    return scenario

