"""Database connection and session utilities with reliable local demo fallback."""

import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger("floodpath.database")

DEFAULT_DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/floodpath"
DEMO_SQLITE_URL = "sqlite:///floodpath_demo.db"

# Register SQLite compilation hooks for GeoAlchemy2 geometries and Postgres UUIDs
try:
    import geoalchemy2.admin.dialects.sqlite as sqlite_admin
    from geoalchemy2 import Geometry
    from geoalchemy2.elements import WKTElement
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    from sqlalchemy.ext.compiler import compiles

    sqlite_admin.after_create = lambda *a, **k: None
    sqlite_admin.before_create = lambda *a, **k: None

    @compiles(Geometry, "sqlite")
    def _compile_geom(el, comp, **kw):
        return "TEXT"

    @compiles(WKTElement, "sqlite")
    def _compile_wkt(el, comp, **kw):
        return comp.process(el.data, **kw) if hasattr(el, "data") else str(el)

    @compiles(PG_UUID, "sqlite")
    def _compile_uuid(type_, comp, **kw):
        return "TEXT"

    Geometry.bind_expression = lambda self, bindvalue: (
        bindvalue.data if hasattr(bindvalue, "data") else bindvalue
    )
    Geometry.column_expression = lambda self, col: col
    Geometry.result_processor = lambda self, dialect, coltype: lambda value: value
except Exception as e:
    logger.debug(f"SQLite geometry compilation setup notice: {e}")


def get_database_url(sync: bool = True) -> str:
    url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL") or DEFAULT_DB_URL
    if sync:
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+psycopg://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


_cached_engine = None


def create_db_engine(url: str | None = None):
    global _cached_engine
    if url is None and _cached_engine is not None:
        return _cached_engine

    db_url = url or get_database_url(sync=True)

    if "postgresql" in db_url:
        connect_args = {"connect_timeout": 2}
        try:
            test_engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
            with test_engine.connect():
                pass
            if url is None:
                _cached_engine = test_engine
            return test_engine
        except Exception as e:
            logger.warning(
                f"PostgreSQL unreachable at {db_url} ({e}). "
                f"Activating self-contained local demonstration database: {DEMO_SQLITE_URL}"
            )
            db_url = DEMO_SQLITE_URL

    if "sqlite" in db_url:
        connect_args = {"check_same_thread": False}
        engine = create_engine(db_url, connect_args=connect_args, poolclass=StaticPool)

        # Auto-initialize and seed demo schema if needed
        try:
            import backend.app.models  # noqa: F401
            from backend.app.models.base import Base

            Base.metadata.create_all(engine)

            from backend.seed.seed_all import run_all_seeds

            run_all_seeds(db_url)
        except Exception as seed_err:
            logger.debug(f"Demo schema initialization notice: {seed_err}")

        if url is None:
            _cached_engine = engine
        return engine

    engine = create_engine(db_url, pool_pre_ping=True)
    if url is None:
        _cached_engine = engine
    return engine


def get_session_factory(engine=None):
    eng = engine or create_db_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=eng)


def SessionLocal():
    """Convenience callable returning a new Session from the default engine."""
    factory = get_session_factory()
    return factory()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
