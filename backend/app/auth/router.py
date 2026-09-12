"""Authentication API endpoints: login, guest session, and session verification."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.jwt import create_access_token
from backend.app.auth.schemas import (
    GuestSessionResponse,
    LoginRequest,
    TokenResponse,
    UserResponse,
)
from backend.app.auth.service import authenticate_user
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate analyst and issue JWT access token",
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email and password, returning a JWT token for analysts."""
    user = authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
    }
    access_token = create_access_token(data=token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
        ),
    )


@router.post(
    "/guest",
    response_model=GuestSessionResponse,
    summary="Initialize an ephemeral guest session without creating a database user",
)
def guest_session():
    """Returns guest session status.

    Per the PRD and Technical Requirements, guest sessions are client-side only
    and do not create any records in the users table.
    """
    return GuestSessionResponse()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Fetch the currently authenticated analyst profile",
)
def get_me(current_user: User = Depends(get_current_user)):
    """Validates the JWT token and returns the current user profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role.value
        if hasattr(current_user.role, "value")
        else str(current_user.role),
    )
