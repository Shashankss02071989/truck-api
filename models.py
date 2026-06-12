from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class TruckORM(Base):
    """SQLAlchemy ORM model for the trucks table."""

    __tablename__ = "trucks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    driver_name: Mapped[str] = mapped_column(String, nullable=False)
    license_plate: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    location: Mapped[str] = mapped_column(String, nullable=False)
    fuel_level: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)


class UserORM(Base):
    """SQLAlchemy ORM model for the users table."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)


class TruckBase(BaseModel):

    """Shared truck fields for create and response schemas."""

    driver_name: str = Field(min_length=1, description="Name of the assigned driver")
    license_plate: str = Field(min_length=1, description="Vehicle license plate")
    location: str = Field(min_length=1, description="Current location")
    fuel_level: float = Field(ge=0, le=100, description="Fuel level as a percentage (0-100)")
    status: Literal["active", "idle", "maintenance", "in_transit"]


class TruckCreate(TruckBase):
    """Schema for creating a new truck (client does not supply id)."""


class TruckUpdate(TruckBase):
    """Schema for fully replacing an existing truck (client does not supply id)."""


class Truck(TruckBase):
    """A truck record returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    username: str = Field(min_length=3, max_length=50, description="Username for login")
    password: str = Field(min_length=8, description="User password")


class User(BaseModel):
    """User record returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class Token(BaseModel):
    """JWT Token response schema."""

    access_token: str
    token_type: str

