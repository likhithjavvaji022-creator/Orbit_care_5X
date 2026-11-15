"""Database engine/session. DATABASE_URL env (default sqlite:///./orbitcare.db)."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = None


def configure(url: str | None = None):
    """(Re)bind the engine; tests call this with a temp SQLite URL."""
    global engine, SessionLocal
    url = url or os.environ.get("DATABASE_URL", "sqlite:///./orbitcare.db")
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    if engine is not None:
        engine.dispose()
    engine = create_engine(url, **kwargs)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine


def init_db():
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


configure()
