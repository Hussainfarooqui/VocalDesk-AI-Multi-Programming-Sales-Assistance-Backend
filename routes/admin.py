"""
VocalDesk – Admin Authentication & User Management Routes
POST /api/admin/login          → JWT token (FR-2, FR-3)
POST /api/admin/register       → Create new user (FR-1)
POST /api/admin/password-reset → Reset password (FR-4)
GET  /api/admin/users          → List users (FR-44)
JWT dependency for protecting admin endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database.connection import get_db
from backend.models.user import User
from backend.services.auth_service import verify_password, create_access_token, decode_access_token, hash_password
from backend.services import email_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin Auth"])

# Type definition for reset payload
from typing import Optional
from pydantic import BaseModel

class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = "staff"

class PasswordReset(BaseModel):
    username: str
    new_password: str

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")


# ─── JWT Guard Dependency ────────────────────────────────────────────────────
def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
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

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


# ─── Login Endpoint (FR-2, FR-3) ────────────────────────────────────────────
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
    user = db.query(User).filter(User.username == form_data.username).first()

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
        "role": user.role,
    }


# ─── Register Endpoint (FR-1) ───────────────────────────────────────────────
@router.post("/register", summary="Register a new user (FR-1)")
def register_user(
    body: UserRegister,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Register a new system user (admin-only).
    """
    username = body.username.strip()
    password = body.password.strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    # Check for existing user
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Username '{username}' already exists.")

    hashed = hash_password(password)
    new_user = User(
        username=username,
        hashed_password=hashed,
        email=body.email,
        full_name=body.full_name,
        role=body.role or "staff",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"New user registered: username='{username}', role='{new_user.role}'")
    return {"success": True, "user": new_user.to_dict()}


# ─── Public Signup Endpoint ───────────────────────────────────────────────────
@router.post("/signup", summary="Public user registration")
def public_signup(
    body: UserRegister,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Register a new user publicly (no admin token required).
    """
    username = body.username.strip()
    password = body.password.strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    # Check for existing user
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Username '{username}' already exists.")

    hashed = hash_password(password)
    new_user = User(
        username=username,
        hashed_password=hashed,
        email=body.email,
        full_name=body.full_name,
        role="user",  # Force role to user for public signups
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if body.email:
        background_tasks.add_task(email_service.send_welcome_email, username, body.email)

    logger.info(f"New public user registered: username='{username}'")
    return {"success": True, "user": new_user.to_dict()}


# ─── Password Reset (FR-4) ──────────────────────────────────────────────────
@router.post("/password-reset", summary="Reset user password (FR-4)")
def reset_password(
    body: PasswordReset,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """
    Reset a user's password (admin-only operation).
    """
    username = body.username.strip()
    new_password = body.new_password.strip()

    if not username or not new_password:
        raise HTTPException(status_code=400, detail="username and new_password are required.")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

    user.hashed_password = hash_password(new_password)
    db.commit()

    logger.info(f"Password reset for user='{username}' by admin='{current_admin.username}'")
    return {"success": True, "message": f"Password reset for '{username}'."}


# ─── User Management (FR-44) ────────────────────────────────────────────────
@router.get("/users", summary="List all users (FR-44)")
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Return all system users (admin-only).

    Returns:
        { success, total, users[] }
    """
    total = db.query(func.count(User.id)).scalar() or 0
    users = db.query(User).order_by(User.created_at.desc()).all()
    return {
        "success": True,
        "total": total,
        "users": [u.to_dict() for u in users],
    }
