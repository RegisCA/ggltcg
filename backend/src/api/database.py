"""
Database connection and session management.

Provides SQLAlchemy engine and session management for PostgreSQL database.
"""

import os
import logging
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import Pool

logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.warning(
        "DATABASE_URL environment variable not set. "
        "Database features will not be available. "
        "Set DATABASE_URL to enable PostgreSQL persistence."
    )
    # Create a dummy engine that won't be used
    # This allows imports to succeed even without a database
    engine = None
    SessionLocal = None
elif DATABASE_URL.startswith('sqlite'):
    # SQLite doesn't support pool_size/max_overflow (uses SingletonThreadPool)
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before use
        echo=False,  # Set to True for SQL query logging during development
    )
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # PostgreSQL or other databases that support connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections before use
        echo=False,  # Set to True for SQL query logging during development
    )
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Log connection pool statistics (useful for debugging)
@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log when a new database connection is created."""
    logger.debug("New database connection established")


@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool."""
    logger.debug("Connection checked out from pool")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI endpoints.
    
    Provides a database session that automatically commits on success
    or rolls back on exception.
    
    Usage:
        @app.get("/games/{game_id}")
        def get_game(game_id: str, db: Session = Depends(get_db)):
            game = db.query(GameModel).filter(GameModel.id == game_id).first()
            return game
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    
    This is called when the application starts. However, in production,
    we use Alembic migrations instead of this method.
    """
    from api.db_models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")


def check_db_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
