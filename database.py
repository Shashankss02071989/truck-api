from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL: str = "sqlite:///./trucks.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for ORM models."""


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed after the request.

    Yields:
        An active SQLAlchemy session bound to the application engine.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create database tables and seed initial truck data if the table is empty."""
    from models import TruckORM

    Base.metadata.create_all(bind=engine)

    seed_trucks: list[dict[str, str | float]] = [
        {
            "driver_name": "John Smith",
            "license_plate": "TX-4821",
            "location": "Dallas, TX",
            "fuel_level": 78.5,
            "status": "in_transit",
        },
        {
            "driver_name": "Maria Garcia",
            "license_plate": "CA-9034",
            "location": "Los Angeles, CA",
            "fuel_level": 42.0,
            "status": "active",
        },
        {
            "driver_name": "Robert Johnson",
            "license_plate": "IL-2156",
            "location": "Chicago, IL",
            "fuel_level": 91.2,
            "status": "idle",
        },
        {
            "driver_name": "Emily Chen",
            "license_plate": "NY-7789",
            "location": "New York, NY",
            "fuel_level": 15.8,
            "status": "maintenance",
        },
        {
            "driver_name": "David Williams",
            "license_plate": "FL-3345",
            "location": "Miami, FL",
            "fuel_level": 63.4,
            "status": "in_transit",
        },
    ]

    with SessionLocal() as db:
        if db.query(TruckORM).first() is not None:
            return

        for truck_data in seed_trucks:
            db.add(TruckORM(**truck_data))
        db.commit()
