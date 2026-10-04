from typing import Generator
from sqlalchemy.orm import Session
from db.database import DatabaseManager


def get_db_session() -> Generator[Session, None, None]:
    """Provee una sesión de base de datos SQLAlchemy por solicitud HTTP."""
    db = DatabaseManager()
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()
