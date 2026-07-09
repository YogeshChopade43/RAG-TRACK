"""
Authentication service for RAG-TRACK.

Provides user registration, login, and token management.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.models.user import User
from app.db.models.token import Token


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user with email and password.
    
    Args:
        db: Database session
        email: User email
        password: Plain text password
        
    Returns:
        User object if authentication successful, None otherwise
    """
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


def register_user(
    db: Session,
    email: str,
    password: str,
    full_name: Optional[str] = None,
) -> User:
    """
    Register a new user.
    
    Args:
        db: Database session
        email: User email
        password: Plain text password
        full_name: Optional full name
        
    Returns:
        Created user object
        
    Raises:
        HTTPException: If email already exists
    """
    existing_user = db.query(User).filter(User.email == email).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    hashed_password = get_password_hash(password)
    
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def logout(db: Session, user_id: uuid.UUID, token: str) -> None:
    """
    Revoke a token for logout.
    
    Args:
        db: Database session
        user_id: User ID
        token: JWT token to revoke
    """
    try:
        payload = decode_token(token)
        expires_at = datetime.fromtimestamp(payload["exp"])
    except Exception:
        return
    
    db_token = Token(
        id=uuid.uuid4(),
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        is_revoked=True,
    )
    
    db.add(db_token)
    db.commit()


def is_token_revoked(db: Session, token: str) -> bool:
    """
    Check if a token has been revoked.
    
    Args:
        db: Database session
        token: JWT token to check
        
    Returns:
        True if token is revoked, False otherwise
    """
    token_record = db.query(Token).filter(Token.token == token).first()
    
    if token_record and token_record.is_revoked:
        return True
    
    return False


def change_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """
    Change user password.
    
    Args:
        db: Database session
        user: User object
        current_password: Current password for verification
        new_password: New password to set
        
    Raises:
        HTTPException: If current password is incorrect
    """
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    user.hashed_password = get_password_hash(new_password)
    db.commit()


def create_tokens(db: Session, user: User) -> dict:
    """
    Create access and refresh tokens for a user.
    
    Args:
        db: Database session
        user: User object
        
    Returns:
        Dictionary with access_token and refresh_token
    """
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }