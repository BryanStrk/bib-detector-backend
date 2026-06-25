# Bib Detector Backend

![Status](https://img.shields.io/badge/status-production-brightgreen)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/fastapi-latest-009688)
![PostgreSQL](https://img.shields.io/badge/postgresql-neon-336791)
![Docker](https://img.shields.io/badge/docker-ready-2496ed)
![License](https://img.shields.io/badge/license-MIT-green)

**FastAPI + SQLModel backend for real-time bib detection in race photography.** Provides OCR-powered athlete identification, privacy-first claim flow, and secure runner galleries with watermarked previews.

**Live:** https://bryanstrike-bib-detector.hf.space

---

## 📋 Table of Contents

- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Architecture](#architecture)
- [Development](#development)
- [Deployment](#deployment)
- [Best Practices](#best-practices)

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | FastAPI | Async web framework, auto-generated OpenAPI docs |
| **ORM** | SQLModel | Type-safe ORM combining Pydantic + SQLAlchemy |
| **Database** | Neon PostgreSQL | Serverless Postgres with auto-scaling |
| **Image Processing** | EasyOCR | Bib number extraction from race photos |
| **Storage** | Cloudinary | Image hosting, transformations, signed URLs |
| **Email** | Resend | Transactional emails for magic links |
| **Auth** | JWT (PyJWT) | Stateless token-based authentication |
| **Validation** | Pydantic | Request/response schema validation |
| **Containerization** | Docker | HuggingFace Spaces deployment |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+**
- **pip** or **uv** (faster alternative)
- **PostgreSQL 14+** (or Neon PostgreSQL account)
- **Git**

### Installation

#### 1. Clone Repository
```bash
git clone https://github.com/BryanStrk/bib-detector-backend.git
cd bib-detector-backend
```

#### 2. Create Virtual Environment
```bash
# Using venv
python3.12 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Or using uv (faster)
uv venv .venv
source .venv/bin/activate
```

#### 3. Install Dependencies
```bash
# Using pip
pip install -r requirements.txt

# Or using uv
uv pip install -r requirements.txt
```

#### 4. Configure Environment Variables

Create `.env` file in project root:

```env
# ============ DATABASE ============
DATABASE_URL=postgresql://user:password@localhost:5432/bib_detector
# For Neon Postgres:
# DATABASE_URL=postgresql://user:password@your-project.neon.tech/bib_detector?sslmode=require

# ============ JWT SECRETS ============
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
ADMIN_SECRET_KEY=your-admin-secret-key-min-32-chars
RUNNER_SECRET_KEY=your-runner-secret-key-min-32-chars
CLAIM_SECRET_KEY=your-claim-secret-key-min-32-chars

# Token expiration (seconds)
ADMIN_TOKEN_EXPIRE_SECONDS=86400      # 24 hours
RUNNER_TOKEN_EXPIRE_SECONDS=86400     # 24 hours
CLAIM_TOKEN_EXPIRE_SECONDS=900        # 15 minutes

# ============ CLOUDINARY ============
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# ============ RESEND (EMAIL) ============
RESEND_API_KEY=your-resend-api-key

# ============ CORS & SECURITY ============
FRONTEND_URL=http://localhost:5173
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# ============ ENVIRONMENT ============
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

**⚠️ Security Note:**
- Add `.env` to `.gitignore` immediately
- **Never commit secrets** to version control
- Use GitHub Secrets for CI/CD deployments
- Rotate secrets periodically in production

#### 5. Initialize Database

```bash
# Run migrations (Alembic)
alembic upgrade head

# Seed test data (optional)
python scripts/seed_db.py
```

#### 6. Run Development Server

```bash
# With auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using the run script
python -m app.main
```

**Access:**
- API: http://localhost:8000
- Swagger UI (Docs): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📡 API Reference

### Authentication Endpoints

#### Admin Login
```
POST /auth/admin/login
Content-Type: application/json

{
  "username": "admin",
  "password": "secure-password"
}

Response: 200 OK
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### Claim Token Verification
```
POST /auth/claims/verify
Content-Type: application/json

{
  "claim_token": "eyJhbGciOiJIUzI1NiIs..."
}

Response: 200 OK
{
  "access_token": "runner-token...",
  "token_type": "bearer",
  "runner_id": "uuid",
  "bib_number": "819"
}
```

#### Get Current User
```
GET /auth/me
Authorization: Bearer <token>

Response: 200 OK
{
  "user_id": "uuid",
  "role": "admin|runner",
  "token_type": "admin|runner",
  "created_at": "2026-06-21T10:00:00Z"
}
```

---

### Detection Endpoints

#### Single Photo OCR
```
POST /api/detect
Content-Type: application/json
Authorization: Bearer <admin-token>

{
  "image_url": "https://example.com/race.jpg",
  "event_id": 1
}

Response: 200 OK
{
  "photo_id": "uuid",
  "detections": [
    {
      "bib": "819",
      "confidence": 0.98,
      "bbox": {
        "x": 100,
        "y": 200,
        "width": 50,
        "height": 70
      }
    },
    {
      "bib": "360",
      "confidence": 0.95,
      "bbox": {
        "x": 300,
        "y": 180,
        "width": 48,
        "height": 68
      }
    }
  ],
  "processed_at": "2026-06-21T10:05:23Z"
}
```

#### Batch Detection
```
POST /api/detect/batch
Content-Type: application/json
Authorization: Bearer <admin-token>

{
  "image_urls": [
    "https://example.com/photo1.jpg",
    "https://example.com/photo2.jpg"
  ],
  "event_id": 1
}

Response: 200 OK
{
  "batch_id": "uuid",
  "processed": 2,
  "failed": 0,
  "results": [
    {
      "image_url": "...",
      "photo_id": "uuid",
      "detections": [...]
    }
  ]
}
```

---

### Photo Endpoints

#### List Photos (Public Gallery)
```
GET /api/photos?event_id=1&limit=20&offset=0
Authorization: Bearer <admin-token>

Response: 200 OK
{
  "total": 150,
  "limit": 20,
  "offset": 0,
  "photos": [
    {
      "id": "uuid",
      "cloudinary_url": "https://res.cloudinary.com/...",
      "preview_url": "https://res.cloudinary.com/.../c_thumb,w_300,h_300/",
      "event_id": 1,
      "detected_bibs": ["819", "360", "281"],
      "confidence_avg": 0.96,
      "created_at": "2026-06-21T10:00:00Z"
    }
  ]
}
```

#### Get Photo Details
```
GET /api/photos/{photo_id}
Authorization: Bearer <admin-token>

Response: 200 OK
{
  "id": "uuid",
  "cloudinary_url": "...",
  "preview_url": "...",
  "event_id": 1,
  "storage_type": "authenticated",
  "detections": [
    {
      "id": "uuid",
      "bib": "819",
      "confidence": 0.98,
      "bbox": {...}
    }
  ]
}
```

#### Get Signed Download URL
```
GET /api/photos/{photo_id}/download
Authorization: Bearer <runner-token>

Response: 200 OK
{
  "signed_url": "https://res.cloudinary.com/.../s_<signature>/",
  "expires_in": 3600,
  "filename": "race-photo.jpg"
}
```

#### Delete Photo
```
DELETE /api/photos/{photo_id}
Authorization: Bearer <admin-token>

Response: 200 OK
{
  "success": true,
  "deleted_id": "uuid"
}
```

---

### Event Endpoints

#### List Events
```
GET /api/events
Authorization: Bearer <admin-token>

Response: 200 OK
[
  {
    "id": 1,
    "name": "Marató 2026",
    "date": "2026-06-21",
    "location": "Barcelona",
    "participants_count": 500,
    "photos_count": 1200,
    "created_at": "2026-06-01T08:00:00Z"
  }
]
```

#### Create Event
```
POST /api/events
Content-Type: application/json
Authorization: Bearer <admin-token>

{
  "name": "Marató 2026",
  "date": "2026-06-21",
  "location": "Barcelona"
}

Response: 201 Created
{
  "id": 1,
  "name": "Marató 2026",
  "date": "2026-06-21",
  "location": "Barcelona",
  "created_at": "2026-06-21T08:00:00Z"
}
```

#### Get Event with Roster
```
GET /api/events/{event_id}
Authorization: Bearer <admin-token>

Response: 200 OK
{
  "id": 1,
  "name": "Marató 2026",
  "participants": [
    {
      "id": "uuid",
      "event_id": 1,
      "bib_number": "819",
      "email": "athlete@example.com",
      "claimed": true,
      "claimed_at": "2026-06-21T10:30:00Z"
    }
  ],
  "total_participants": 500
}
```

#### Bulk Import Participants
```
POST /api/events/{event_id}/participants
Content-Type: application/json
Authorization: Bearer <admin-token>

{
  "participants": [
    { "bib_number": "819", "email": "bryanpaicoalbines97@gmail.com" },
    { "bib_number": "360", "email": "athlete2@example.com" }
  ]
}

Response: 200 OK
{
  "imported": 2,
  "duplicates": 0,
  "invalid": 0,
  "created_at": "2026-06-21T09:00:00Z"
}
```

---

### Claim Flow (Runner Authentication)

#### Request Claim Token
```
POST /api/claims
Content-Type: application/json

{
  "event_id": 1,
  "bib_number": "819",
  "email": "bryanpaicoalbines97@gmail.com"
}

Response: 200 OK (always, anti-enumeration)
{
  "status": "email_sent|already_claimed",
  "message": "Check your inbox for the verification link"
}
```

#### Verify & Exchange Claim Token
```
POST /api/claims/verify
Content-Type: application/json

{
  "claim_token": "eyJhbGciOiJIUzI1NiIs..."
}

Response: 200 OK
{
  "access_token": "runner-jwt-token...",
  "token_type": "bearer",
  "runner_id": "uuid",
  "bib_number": "819",
  "expires_in": 86400
}
```

---

### Runner Private Gallery

#### Get My Photos (Filtered by Bib)
```
GET /api/me/photos?limit=20&offset=0
Authorization: Bearer <runner-token>

Response: 200 OK
{
  "total": 5,
  "photos": [
    {
      "id": "uuid",
      "preview_url": "https://res.cloudinary.com/.../c_thumb,w_300,h_300,o_50,l_text:Trebuchet_45_bold:BIB%20DETECTOR/",
      "event_id": 1,
      "detections": [
        {
          "bib": "819",
          "confidence": 0.98
        }
      ],
      "created_at": "2026-06-21T10:00:00Z"
    }
  ]
}
```

---

### Admin Endpoints

#### Dashboard Statistics
```
GET /api/admin/stats
Authorization: Bearer <admin-token>

Response: 200 OK
{
  "photos_processed": 1250,
  "bibs_detected": 3890,
  "avg_confidence": 0.96,
  "events_count": 5,
  "runners_claimed": 425,
  "processing_time_avg_ms": 2340
}
```

#### Audit Logs
```
GET /api/admin/logs?limit=50&offset=0
Authorization: Bearer <admin-token>

Response: 200 OK
{
  "logs": [
    {
      "id": "uuid",
      "timestamp": "2026-06-21T10:05:23Z",
      "action": "PHOTO_DETECTED",
      "user_id": "uuid",
      "details": {
        "photo_id": "uuid",
        "bibs_found": 3
      }
    }
  ]
}
```

---

## 🏗️ Architecture

### Layered Structure

```
FastAPI Routes (app/api/routes/)
         ↓
Business Logic (app/services/)
         ↓
Database Access (app/db/repositories/)
         ↓
SQLModel + Pydantic (app/models/ + app/schemas/)
         ↓
PostgreSQL (Neon)
```

### Core Services

#### `OCRService`
- Coordinates EasyOCR extraction
- Manages confidence thresholds
- Returns structured detection objects
- Handles concurrent batch processing

#### `CloudinaryService`
- Upload & transforms images
- Generates watermarked previews
- Creates signed URLs (1-hour expiration)
- Handles storage_type (public vs authenticated)

#### `AuthService`
- JWT token generation & validation
- Role-based access control (admin vs runner)
- Token expiration management
- Claims token (15min) → Runner token (24h) exchange

#### `EmailService` (Resend)
- Sends magic link emails
- Anti-enumeration: always returns 200 on claim request
- Customizable email templates

---

## 🛠️ Development

### Project Structure

```
bib-detector-backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # JWT endpoints
│   │   │   ├── detect.py        # OCR endpoints
│   │   │   ├── photos.py        # Photo gallery
│   │   │   ├── events.py        # Event management
│   │   │   ├── claims.py        # Runner claim flow
│   │   │   └── admin.py         # Admin operations
│   │   └── deps.py              # Shared dependencies
│   ├── core/
│   │   ├── config.py            # Settings, env vars
│   │   ├── security.py          # JWT utilities
│   │   ├── exceptions.py        # Custom exceptions
│   │   └── constants.py
│   ├── models/
│   │   ├── photo.py             # Photo model
│   │   ├── detection.py         # Detection model
│   │   ├── event.py             # Event model
│   │   ├── participant.py       # Participant model
│   │   ├── user.py              # User model
│   │   └── claim.py             # Claim token model
│   ├── schemas/
│   │   ├── photo.py             # Photo DTOs
│   │   ├── detection.py         # Detection DTOs
│   │   ├── event.py             # Event DTOs
│   │   └── user.py              # User DTOs
│   ├── services/
│   │   ├── ocr_service.py       # EasyOCR wrapper
│   │   ├── cloudinary_service.py # Image storage
│   │   ├── email_service.py     # Resend integration
│   │   ├── auth_service.py      # JWT management
│   │   └── storage_service.py   # File handling
│   ├── db/
│   │   ├── session.py           # SQLModel session
│   │   ├── init_db.py           # DB initialization
│   │   └── repositories/        # Data access layer
│   │       ├── photo_repo.py
│   │       ├── event_repo.py
│   │       └── user_repo.py
│   ├── middleware/
│   │   ├── cors.py              # CORS configuration
│   │   ├── error_handler.py     # Global exception handler
│   │   └── logging.py           # Request/response logging
│   ├── utils/
│   │   ├── validators.py        # Input validation
│   │   ├── helpers.py           # Utility functions
│   │   └── decorators.py        # Custom decorators
│   └── main.py                  # FastAPI app initialization
├── alembic/                     # Database migrations
├── scripts/
│   ├── seed_db.py              # Test data
│   └── health_check.py         # Liveness probe
├── tests/
│   ├── test_auth.py
│   ├── test_detect.py
│   ├── test_claims.py
│   └── conftest.py             # Pytest fixtures
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt
├── .env.example
├── main.py                      # Entry point
└── README.md
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py -v
```

### Linting & Formatting

```bash
# Install dev tools
pip install black flake8 isort

# Format code
black app/
isort app/

# Check style
flake8 app/
```

---

## 🐳 Deployment

### Local Docker

```bash
# Build image
docker build -t bib-detector-backend .

# Run container
docker run \
  -p 7860:7860 \
  --env-file .env \
  bib-detector-backend

# Or with docker-compose
docker-compose up --build
```

### HuggingFace Spaces (Production)

**Prerequisites:**
- HuggingFace account + Space created
- Docker + Docker Hub push (or direct git push)

**Automatic Deployment:**
```bash
# Push to HF Space
git remote add hf https://huggingface.co/spaces/BryanStrike/bib-detector
git push hf main
```

**Manual Build:**
```bash
docker build -t bib-detector-backend .
docker tag bib-detector-backend:latest \
  bryanstrike/bib-detector-backend:latest
docker push bryanstrike/bib-detector-backend:latest
```

**Live:** https://bryanstrike-bib-detector.hf.space

### Health Check

```bash
curl -s https://bryanstrike-bib-detector.hf.space/health | jq
```

---

## ✅ Best Practices Implemented

### 1. **Clean Architecture**
- Routes → Services → Repositories → Models
- Clear separation of concerns
- Dependency injection via FastAPI `Depends()`

### 2. **Error Handling**
```python
# Custom exceptions
class BibNotFoundError(Exception):
    pass

class UnauthorizedError(Exception):
    pass

# Global exception handler
@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(request, exc):
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)}
    )
```

### 3. **Security**
- **JWT Tokens:** Role-based (admin vs runner)
- **Secrets:** Environment variables, never hardcoded
- **CORS:** Whitelist trusted origins
- **Input Validation:** Pydantic schemas
- **Rate Limiting:** (Configured via middleware)

### 4. **Type Safety**
```python
# SQLModel combines Pydantic + SQLAlchemy
class Photo(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: int = Field(foreign_key="event.id")
    cloudinary_url: str
    storage_type: Literal["upload", "authenticated"] = "upload"
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 5. **Async-First Design**
```python
@app.post("/api/detect")
async def detect_bibs(
    request: DetectRequest,
    db: Session = Depends(get_session)
) -> DetectResponse:
    # Async I/O for Cloudinary, DB queries
    photo = await cloudinary_service.upload(request.image_url)
    detections = await ocr_service.extract_bibs(photo.url)
    await db.add(photo)
    return DetectResponse(detections=detections)
```

### 6. **Database**
- **Migrations:** Alembic versioning
- **Indexes:** On event_id, bib_number, email
- **Constraints:** UNIQUE(event_id + bib_number)
- **Relationships:** Foreign keys, cascading deletes

### 7. **Logging**
```python
# Structured logging (JSON format)
import logging

logger = logging.getLogger(__name__)

logger.info(
    "photo_detected",
    extra={
        "photo_id": photo.id,
        "bibs_count": len(detections),
        "processing_time_ms": elapsed_ms
    }
)
```

---

## 📚 Additional Resources

- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **SQLModel Docs:** https://sqlmodel.tiangolo.com/
- **Pydantic Docs:** https://docs.pydantic.dev/
- **EasyOCR Docs:** https://github.com/JaidedAI/EasyOCR
- **Cloudinary API:** https://cloudinary.com/documentation

---

## 🤝 Contributing

1. **Branch:** `git checkout -b feat/your-feature`
2. **Code:** Follow style (Black, isort, flake8)
3. **Test:** `pytest tests/`
4. **Commit:** `git commit -m "feat: add bib validation"`
5. **Push:** `git push origin feat/your-feature`

**Conventional Commits:**
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code restructuring
- `docs:` Documentation
- `test:` Adding tests

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

---

**Built with ❤️ by Bryan Paico Albines**  
*Fast, accurate bib detection for modern race photography.*
