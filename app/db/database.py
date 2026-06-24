"""Database session management"""

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL
from app.db import Base

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session():
    """Context manager for DB sessions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# Auto-create tables on import
init_db()
