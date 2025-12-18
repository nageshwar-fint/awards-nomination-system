from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    """FastAPI-friendly session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
