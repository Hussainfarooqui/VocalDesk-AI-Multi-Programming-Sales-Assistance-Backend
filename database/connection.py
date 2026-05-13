"""
VocalDesk – Database Connection
Exclusive Engine: Microsoft SQL Server (SSMS) via pyodbc.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Default to local SQLEXPRESS if DATABASE_URL is missing
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mssql+pyodbc://@localhost\\SQLEXPRESS/VocalDesk?driver=ODBC+Driver+17+for+SQL+Server&Trusted_Connection=yes&TrustServerCertificate=yes"
)

# Enforce MSSQL – Fail fast if another engine is attempted
if "mssql" not in DATABASE_URL.lower():
    logger.error(f"Unsupported database engine detected: {DATABASE_URL.split('://')[0]}. VocalDesk requires MS SQL Server.")
    raise ImportError("VocalDesk is configured for MS SQL Server ONLY. Please update DATABASE_URL in .env.")

# SQL Server (SSMS) – Windows Authentication / Trusted Connection
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)
logger.info("Database engine: Microsoft SQL Server (SSMS)")

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
    from backend.models.user import User            # noqa
    from backend.models.conversation import Conversation # noqa
    from backend.models.voice_log import VoiceLog    # noqa
    from backend.models.analytics import Analytics    # noqa
    from backend.models.workflow_log import WorkflowLog # noqa

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified successfully.")

    # Seed default admin user if none exist
    _seed_admin_user()


def _seed_admin_user():
    """Create the default admin user from environment variables if not present."""
    from backend.models.user import User
    from passlib.context import CryptContext

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == admin_username).first()
        if existing:
            logger.info(f"Admin user '{admin_username}' already exists.")
            return

        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # Ensure password is not too long for bcrypt and handled as string
        safe_password = str(admin_password)[:72]
        hashed = pwd_ctx.hash(safe_password)
        admin = User(username=admin_username, hashed_password=hashed, role="admin")
        db.add(admin)
        db.commit()
        logger.info(f"Admin user '{admin_username}' seeded successfully.")
    except Exception as e:
        logger.error(f"Admin seeding failed: {e}")
        db.rollback()
    finally:
        db.close()
