"""
VocalDesk – Admin Authentication Route
POST /api/admin/login → JWT token
JWT dependency for protecting admin endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.models.admin_user import AdminUser
from backend.services.auth_service import verify_password, create_access_token, decode_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")


# ─── JWT Guard Dependency ────────────────────────────────────────────────────
def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AdminUser:
    """
    FastAPI dependency: validates Bearer JWT and returns the admin user.
    Raises 401 if token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = db.query(AdminUser).filter(AdminUser.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


# ─── Login Endpoint ──────────────────────────────────────────────────────────
@router.post("/login", summary="Admin Login → JWT")
def admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authenticate an admin user and return a JWT access token.

    Body (form-encoded): username, password

    Returns:
        { access_token, token_type }
    """
    user = db.query(AdminUser).filter(AdminUser.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed admin login attempt for username='{form_data.username}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is disabled",
        )

    access_token = create_access_token(data={"sub": user.username})
    logger.info(f"Admin login successful: username='{user.username}'")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
    }
