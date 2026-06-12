# Truck Details API

A FastAPI service for managing truck fleet information. The API provides JWT-authenticated CRUD operations over truck records stored in SQLite, including driver details, location, fuel level, and operational status.

## Features

- **Authentication** — User registration and JWT-based login (OAuth2 password flow)
- **Truck management** — Full CRUD: list, retrieve, create, update, and delete trucks
- **Persistence** — SQLite database via SQLAlchemy ORM (`trucks.db`)
- **Seed data** — Five sample trucks are inserted automatically on first startup
- **Validation** — Pydantic schemas with field constraints (e.g. fuel level 0–100)
- **OpenAPI docs** — Auto-generated Swagger UI and ReDoc

## Project Structure

| File            | Purpose                                              |
|-----------------|------------------------------------------------------|
| `main.py`       | FastAPI app, route handlers, and application lifespan |
| `models.py`     | SQLAlchemy ORM models and Pydantic request/response schemas |
| `auth.py`       | Password hashing, JWT creation, and current-user dependency |
| `database.py`   | Database engine, session factory, and seed initialization |
| `requirements.txt` | Python dependencies                             |

## Prerequisites

- Python 3.10 or higher

## Setup

1. Clone or download this project and open a terminal in the project directory.

2. Create and activate a virtual environment:

   **Windows (PowerShell):**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

   **macOS / Linux:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Run the Server

Start the API with Uvicorn:

```bash
uvicorn main:app --reload
```

The server runs at [http://127.0.0.1:8000](http://127.0.0.1:8000).

On startup, the application creates database tables and seeds five sample trucks if the `trucks` table is empty.

## Authentication

All `/trucks` endpoints require a valid JWT bearer token. Auth endpoints are public.

### Register a user

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret123"}'
```

| Field      | Constraints        |
|------------|--------------------|
| `username` | 3–50 characters    |
| `password` | Minimum 8 characters |

Returns `201 Created` with `{ "id", "username" }`. Returns `400` if the username is already taken.

### Login

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret123"
```

Returns:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Tokens expire after **30 minutes**. Use the token in subsequent requests:

```bash
Authorization: Bearer <access_token>
```

## API Endpoints

### Authentication

| Method | Endpoint          | Auth | Status | Description              |
|--------|-------------------|------|--------|--------------------------|
| POST   | `/auth/register`  | No   | 201    | Register a new user      |
| POST   | `/auth/login`     | No   | 200    | Obtain a JWT access token |

### Trucks

| Method | Endpoint           | Auth | Status | Description                    |
|--------|--------------------|------|--------|--------------------------------|
| GET    | `/trucks`          | Yes  | 200    | List all trucks (ordered by ID) |
| POST   | `/trucks`          | Yes  | 201    | Create a new truck             |
| GET    | `/trucks/{truck_id}` | Yes | 200  | Get a single truck by ID       |
| PUT    | `/trucks/{truck_id}` | Yes | 200  | Replace an existing truck      |
| DELETE | `/trucks/{truck_id}` | Yes | 204  | Delete a truck by ID           |

Path parameter `truck_id` must be a positive integer (`> 0`).

### Truck Fields

| Field           | Type   | Description                                      |
|-----------------|--------|--------------------------------------------------|
| `id`            | int    | Unique truck identifier (auto-generated)         |
| `driver_name`   | string | Name of the assigned driver (min 1 character)    |
| `license_plate` | string | Vehicle license plate (unique, min 1 character)  |
| `location`      | string | Current location (min 1 character)               |
| `fuel_level`    | float  | Fuel level as a percentage (0–100)               |
| `status`        | string | One of: `active`, `idle`, `maintenance`, `in_transit` |

Create and update requests use the same fields except `id` (supplied via the path on update).

### HTTP Status Codes

| Code | When                                              |
|------|---------------------------------------------------|
| 200  | Successful read or update                         |
| 201  | User or truck created                             |
| 204  | Truck deleted (no response body)                  |
| 400  | Duplicate username on registration                |
| 401  | Missing/invalid token or incorrect login credentials |
| 404  | Truck not found                                   |
| 409  | Duplicate license plate on create or update       |
| 422  | Request body or path parameter validation failed  |

## Example Requests

Set a token variable after logging in:

```bash
TOKEN="<your-access-token>"
```

List all trucks:

```bash
curl http://127.0.0.1:8000/trucks \
  -H "Authorization: Bearer $TOKEN"
```

Get truck by ID:

```bash
curl http://127.0.0.1:8000/trucks/1 \
  -H "Authorization: Bearer $TOKEN"
```

Create a truck:

```bash
curl -X POST http://127.0.0.1:8000/trucks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "driver_name": "Jane Doe",
    "license_plate": "WA-1234",
    "location": "Seattle, WA",
    "fuel_level": 55.0,
    "status": "active"
  }'
```

Update a truck:

```bash
curl -X PUT http://127.0.0.1:8000/trucks/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "driver_name": "John Smith",
    "license_plate": "TX-4821",
    "location": "Austin, TX",
    "fuel_level": 60.0,
    "status": "in_transit"
  }'
```

Delete a truck:

```bash
curl -X DELETE http://127.0.0.1:8000/trucks/1 \
  -H "Authorization: Bearer $TOKEN"
```

## Database

- **Engine:** SQLite (`sqlite:///./trucks.db`)
- **Tables:** `trucks`, `users`
- **Seeding:** On first run, five trucks are inserted if the table is empty (Dallas, Los Angeles, Chicago, New York, Miami)

To reset data, stop the server, delete `trucks.db`, and restart.

## Security Notes

This project uses a hardcoded JWT secret key in `auth.py` for development convenience. For production deployments, move `SECRET_KEY`, `ALGORITHM`, and `ACCESS_TOKEN_EXPIRE_MINUTES` to environment variables and use a strong, randomly generated secret.

## Interactive Documentation

FastAPI provides auto-generated API docs:

- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

Use the **Authorize** button in Swagger UI to paste a bearer token when testing protected endpoints.

## Dependencies

| Package              | Purpose                          |
|----------------------|----------------------------------|
| `fastapi`            | Web framework                    |
| `uvicorn`            | ASGI server                      |
| `sqlalchemy`         | ORM and database access          |
| `python-jose`        | JWT encoding/decoding            |
| `passlib[bcrypt]`    | Password hashing                 |
| `python-multipart`   | OAuth2 form login support        |
