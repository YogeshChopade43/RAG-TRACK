"""
Database session management for RAG-TRACK.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def get_engine():
    """Get database engine."""
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return create_engine(settings.database_url)


def get_session_local():
    """Get session factory."""
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


SessionLocal = None


def get_db() -> Generator:
    """
    Get database session.
    
    Yields:
        Database session
    """
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = get_session_local()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from app.db.base import Base
    
    engine = get_engine()
    Base.metadata.create_all(bind=engine)