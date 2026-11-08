from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import get_settings

settings = get_settings()

# Hosted Postgres providers often hand out "postgres://" URLs, which SQLAlchemy 2 rejects
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import all models here to ensure they're registered with Base
    from models import Machine, Alert, Mechanic, SensorReading, MaintenanceSchedule, NotificationLog
    Base.metadata.create_all(bind=engine)
