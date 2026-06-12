from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from database import get_db, init_db
from models import (
    Token,
    Truck,
    TruckCreate,
    TruckORM,
    TruckUpdate,
    User,
    UserCreate,
    UserORM,
)

SessionDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[UserORM, Depends(get_current_user)]

TRUCKS_RATE_LIMIT: str = "10/minute"
AUTH_RATE_LIMIT: str = "5/minute"

limiter = Limiter(key_func=get_remote_address)
trucks_rate_limit = limiter.shared_limit(TRUCKS_RATE_LIMIT, scope="trucks")
auth_rate_limit = limiter.shared_limit(AUTH_RATE_LIMIT, scope="auth")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database on application startup."""
    init_db()
    yield


app = FastAPI(
    title="Truck Details API",
    description="API for managing and retrieving truck information.",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.post("/auth/register", response_model=User, status_code=status.HTTP_201_CREATED)
@auth_rate_limit
def register(request: Request, user_in: UserCreate, db: SessionDep) -> UserORM:
    """Register a new user.

    Raises:
        HTTPException: 429 if the auth rate limit is exceeded.
    """
    existing_user = db.query(UserORM).filter(UserORM.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    user = UserORM(
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        ) from None

    db.refresh(user)
    return user


@app.post("/auth/login", response_model=Token)
@auth_rate_limit
def login(
    request: Request,
    db: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> dict[str, str]:
    """Login to get an access token.

    Raises:
        HTTPException: 429 if the auth rate limit is exceeded.
    """
    user = db.query(UserORM).filter(UserORM.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


def _get_truck_or_404(db: Session, truck_id: int) -> TruckORM:

    """Return a truck ORM record by ID.

    Args:
        db: Active database session.
        truck_id: Unique identifier of the truck to locate.

    Returns:
        The matching truck ORM record.

    Raises:
        HTTPException: 404 if no truck exists with the given ID.
    """
    truck = db.get(TruckORM, truck_id)
    if truck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Truck with id {truck_id} not found",
        )
    return truck


def _get_truck_by_license_plate(db: Session, license_plate: str) -> TruckORM | None:
    """Return a truck ORM record by license plate, if one exists.

    Args:
        db: Active database session.
        license_plate: License plate value to search for.

    Returns:
        The matching truck ORM record, or None if not found.
    """
    return db.query(TruckORM).filter(TruckORM.license_plate == license_plate).first()


def _orm_to_schema(truck: TruckORM) -> Truck:
    """Convert a SQLAlchemy truck record to a Pydantic response schema.

    Args:
        truck: ORM truck instance loaded from the database.

    Returns:
        Validated Pydantic truck schema for API responses.
    """
    return Truck.model_validate(truck)


@app.get("/trucks", response_model=list[Truck])
@trucks_rate_limit
def list_trucks(request: Request, db: SessionDep, current_user: CurrentUserDep) -> list[Truck]:
    """Return a list of all trucks.

    Raises:
        HTTPException: 429 if the trucks rate limit is exceeded.
    """
    trucks = db.query(TruckORM).order_by(TruckORM.id).all()
    return [_orm_to_schema(truck) for truck in trucks]


@app.post("/trucks", response_model=Truck, status_code=status.HTTP_201_CREATED)
@trucks_rate_limit
def create_truck(
    request: Request,
    truck_in: TruckCreate,
    db: SessionDep,
    current_user: CurrentUserDep,
) -> Truck:
    """Create a new truck and return the created record.

    Raises:
        HTTPException: 409 if a truck with the same license plate already exists.
        HTTPException: 429 if the trucks rate limit is exceeded.
    """
    if _get_truck_by_license_plate(db, truck_in.license_plate) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Truck with license plate {truck_in.license_plate!r} already exists",
        )

    truck = TruckORM(**truck_in.model_dump())
    db.add(truck)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Truck with license plate {truck_in.license_plate!r} already exists",
        ) from None

    db.refresh(truck)
    return _orm_to_schema(truck)


@app.get("/trucks/{truck_id}", response_model=Truck)
@trucks_rate_limit
def get_truck(
    request: Request,
    truck_id: int,
    db: SessionDep,
    current_user: CurrentUserDep,
) -> Truck:
    """Return a single truck by ID.

    Raises:
        HTTPException: 404 if no truck exists with the given ID.
        HTTPException: 429 if the trucks rate limit is exceeded.
    """
    truck = _get_truck_or_404(db, truck_id)
    return _orm_to_schema(truck)


@app.put("/trucks/{truck_id}", response_model=Truck, status_code=status.HTTP_200_OK)
@trucks_rate_limit
def update_truck(
    request: Request,
    truck_in: TruckUpdate,
    db: SessionDep,
    current_user: CurrentUserDep,
    truck_id: int = Path(gt=0, description="Unique identifier of the truck to update"),
) -> Truck:
    """Replace an existing truck with the provided data.

    Args:
        truck_in: Full truck payload (id is taken from the path, not the body).
        db: Active database session.
        current_user: The authenticated user.
        truck_id: Unique identifier of the truck to update.

    Returns:
        The updated truck record.

    Raises:
        HTTPException: 404 if no truck exists with the given ID.
        HTTPException: 409 if another truck already uses the same license plate.
        HTTPException: 429 if the trucks rate limit is exceeded.
    """
    truck = _get_truck_or_404(db, truck_id)

    existing = _get_truck_by_license_plate(db, truck_in.license_plate)
    if existing is not None and existing.id != truck_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Truck with license plate {truck_in.license_plate!r} already exists",
        )

    for field, value in truck_in.model_dump().items():
        setattr(truck, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Truck with license plate {truck_in.license_plate!r} already exists",
        ) from None

    db.refresh(truck)
    return _orm_to_schema(truck)


@app.delete("/trucks/{truck_id}", status_code=status.HTTP_204_NO_CONTENT)
@trucks_rate_limit
def delete_truck(
    request: Request,
    db: SessionDep,
    current_user: CurrentUserDep,
    truck_id: int = Path(gt=0, description="Unique identifier of the truck to delete"),
) -> None:
    """Remove a truck by ID.

    Args:
        db: Active database session.
        current_user: The authenticated user.
        truck_id: Unique identifier of the truck to delete.

    Raises:
        HTTPException: 404 if no truck exists with the given ID.
        HTTPException: 429 if the trucks rate limit is exceeded.
    """
    truck = _get_truck_or_404(db, truck_id)
    db.delete(truck)
    db.commit()

