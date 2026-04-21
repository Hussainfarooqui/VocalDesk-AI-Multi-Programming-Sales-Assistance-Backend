"""
VocalDesk – Database Connection
SQLAlchemy engine, session factory, dependency injection, and admin seeding.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@postgres:5432/vocaldesk"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create all tables defined in models and seed admin user if missing."""
    # Import models to register them with Base
    from backend.models.lead import Lead           # noqa
    from backend.models.admin_user import AdminUser  # noqa

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified successfully.")

    # Seed default admin user if none exist
    _seed_admin_user()


def _seed_admin_user():
    """Create the default admin user from environment variables if not present."""
    from backend.models.admin_user import AdminUser
    from passlib.context import CryptContext

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "vocaldesk_admin_2024")

    db = SessionLocal()
    try:
        existing = db.query(AdminUser).filter(AdminUser.username == admin_username).first()
        if existing:
            logger.info(f"Admin user '{admin_username}' already exists.")
            return

        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_ctx.hash(admin_password)
        admin = AdminUser(username=admin_username, hashed_password=hashed)
        db.add(admin)
        db.commit()
        logger.info(f"Admin user '{admin_username}' seeded successfully.")
    except Exception as e:
        logger.error(f"Admin seeding failed: {e}")
        db.rollback()
    finally:
        db.close()
