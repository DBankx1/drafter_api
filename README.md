# Drafter API

A FastAPI-based backend service for managing business proposals, knowledge bases, and AI-powered chat functionality with Celery async task processing.

## Overview

Drafter API provides a comprehensive REST API for:

- **Authentication** — JWT-based user and business authentication via Supabase
- **Business Management** — Multi-tenant business/company data management
- **Knowledge Base** — Document ingestion, chunking, and vector embeddings for semantic search
- **Chat & Proposals** — AI-powered conversations and proposal generation with LLM integration
- **Real-time Communication** — WebSocket support for live chat updates
- **Async Tasks** — Background job processing for long-running operations (document ingestion, etc.)

## Tech Stack

### Core Framework

- **FastAPI** (>= 0.128.0) — Modern async web framework with automatic API documentation
- **Python** 3.12+ — Latest Python with async/await support

### Database & Storage

- **PostgreSQL 16 with pgvector** — Relational DB + vector similarity search for embeddings
- **SQLAlchemy** (>= 2.0.46) — Async ORM for database operations
- **asyncpg** (>= 0.31.0) — High-performance async PostgreSQL driver
- **Supabase** (>= 2.27.2) — Authentication, storage, and managed database
- **Redis** (7-alpine) — Session store, Celery broker/backend

### LLM & AI

- **OpenAI API** — LLM for proposal generation and embeddings
- **LangChain** — Text splitting and document processing (langchain-text-splitters)
- **pgvector** — Vector similarity search for knowledge base retrieval

### Document Processing

- **PyMuPDF** (>= 1.27.2.2) — PDF parsing and text extraction
- **BeautifulSoup4** (>= 4.14.3) — HTML/XML parsing

### Task Processing

- **Celery** (>= 5.6.3) — Distributed task queue for async operations
- **python-jose** — JWT token handling and verification

### Utilities

- **httpx** — Async HTTP client
- **greenlet** — Lightweight concurrency primitive

## Getting Started

### Prerequisites

- **Docker & Docker Compose** — For containerized development
- **.env file** — Environment variables (see `.env.example` below)

### Installation & Running with Docker

1. **Clone the repository** and navigate to the project directory:

   ```bash
   cd drafter_api
   ```

2. **Create a `.env` file** in the project root with the following variables:

   ```env
   # Database
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_secure_password
   POSTGRES_DB=drafter_db

   # PgAdmin (optional, for database UI)
   PGADMIN_EMAIL=admin@example.com
   PGADMIN_PASSWORD=admin_password

   # OpenAI
   OPENAI_API_KEY=sk-...your_openai_key...

   # Supabase
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_JWT_URL=https://your-project.supabase.co/auth/v1
   SUPABASE_PUBLISHABLE_KEY=your_anon_key
   SUPABASE_SECRET_KEY=your_service_role_key
   SUPABASE_JWT_SECRET=your_jwt_secret
   SUPABASE_AUDIENCE=authenticated
   SUPABASE_STORAGE_BUCKET=knowledge-bases

   # API Configuration (optional)
   API_V1_STR=/api/v1
   ALGORITHM=ES256
   EMBEDDING_MODEL=text-embedding-3-small
   EMBEDDING_DIM=1536
   MAX_PDF_SIZE_MB=20
   ```

3. **Start all services**:

   ```bash
   docker-compose up
   ```

   This will start:
   - **PostgreSQL** on `localhost:5432`
   - **Redis** on `localhost:6379`
   - **PgAdmin** on `http://localhost:5050` (optional database UI)
   - **Drafter API** on `http://localhost:8000` with auto-reload enabled

4. **Access the API**:
   - Main app: http://localhost:8000
   - Interactive API docs: http://localhost:8000/docs
   - Alternative API docs: http://localhost:8000/redoc
   - Health check: http://localhost:8000/health

### Running Locally (without Docker)

If you prefer running locally with `uv`:

1. **Install uv package manager**:

   ```bash
   pip install uv
   ```

2. **Install dependencies**:

   ```bash
   uv pip install -r requirements.txt
   ```

3. **Start PostgreSQL and Redis** (ensure they're running):

   ```bash
   # On macOS with Homebrew
   brew services start postgresql
   brew services start redis
   ```

4. **Run the development server**:
   ```bash
   uv run fastapi dev --host 0.0.0.0 --port 8000
   ```

## Project Structure

```
app/
├── main.py                          # FastAPI app entry point
├── api/
│   ├── main.py                      # API router aggregation
│   └── routes/                      # Endpoint handlers
│       ├── auth.py                  # Authentication endpoints
│       ├── business.py              # Business management
│       ├── chat.py                  # Real-time chat
│       ├── knowledge_base.py        # Document ingestion API
│       └── pricing.py               # Pricing configuration
├── core/
│   ├── config.py                    # Settings management (uses pydantic-settings)
│   ├── security.py                  # JWT and auth utilities
│   ├── lifespan.py                  # App startup/shutdown hooks
│   ├── logging.py                   # Logging configuration
│   ├── celery_app.py                # Celery task queue config
│   ├── supabase_client.py           # Supabase initialization
│   └── middlewares/                 # Request/response middleware
│       ├── auth.py                  # Auth middleware
│       └── business_auth.py         # Business-level auth
├── infrastructure/
│   ├── database/
│   │   └── db.py                    # SQLAlchemy setup, table creation
│   ├── repository/                  # Data access layer (Repository pattern)
│   │   ├── base_repository.py       # Base CRUD operations
│   │   ├── business_repository.py   # Business data access
│   │   ├── message_repository.py    # Chat messages
│   │   └── knowledge_base/          # Knowledge base data access
│   ├── agents/
│   │   └── proposal_agent.py        # LLM agent for proposals
│   ├── prompts/
│   │   └── proposal_prompts.py      # LLM prompt templates
│   ├── supabase/
│   │   └── storage.py               # Supabase file storage
│   ├── workers/
│   │   └── tasks/                   # Celery async tasks
│   │       └── knowledge_base_injestion_task.py  # Document processing
│   └── websockets/
│       └── chat_socket_manager.py   # WebSocket connection management
├── models/
│   ├── entity/                      # SQLAlchemy ORM models
│   │   ├── base.py                  # Base entity with timestamps
│   │   ├── business.py              # Business entity
│   │   ├── conversation.py          # Chat conversation
│   │   ├── message.py               # Chat message
│   │   ├── knowledge_base.py        # Knowledge base
│   │   ├── pricing_config.py        # Pricing configuration
│   │   ├── proposal.py              # Proposal data
│   │   └── widget_settings.py       # Widget configuration
│   ├── dto/                         # Request/response DTOs
│   │   ├── auth.py                  # Auth request/response models
│   │   ├── business.py              # Business DTOs
│   │   ├── knowledge_base.py        # KB DTOs
│   │   └── pricing.py               # Pricing DTOs
│   └── enums/                       # Enum definitions
│       ├── chat_roles.py            # User/Assistant roles
│       ├── knowledge_base_type.py   # KB types (PDF, etc.)
│       ├── pricing_type.py          # Pricing models
│       └── proposal_status.py       # Proposal statuses
└── services/                        # Business logic layer
    ├── auth_service.py              # Authentication logic
    ├── business_service.py          # Business operations
    ├── chat_service.py              # Chat session management
    ├── pricing_config_service.py    # Pricing logic
    ├── supabase_storage.py          # Storage operations
    └── knowledge_base/
        ├── knowledge_base_service.py  # KB orchestration
        ├── chunker.py               # Document chunking (token-based)
        ├── embedder.py              # Vector embeddings (OpenAI)
        ├── injestion.py             # Document ingestion pipeline
        └── parsers/                 # Format-specific parsers (PDF, etc.)

scripts/
├── init.sql                         # Database initialization schema

docker-compose.yml                   # Multi-container development environment
Dockerfile.dev                       # Development container image
requirements.txt                     # Python dependencies
pyproject.toml                       # Project config, Python version
```

## Key Features

### 1. Multi-Tenant Architecture

- Businesses are isolated tenants with their own data
- Business-level authentication middleware enforces data isolation

### 2. Knowledge Base Management

- **Document Ingestion** — Upload PDFs, extract text with PyMuPDF
- **Smart Chunking** — Token-aware splitting using LangChain
- **Vector Embeddings** — OpenAI embeddings stored in pgvector
- **Semantic Search** — PostgreSQL similarity search on vectors
- **Async Processing** — Celery tasks process documents in background

### 3. AI-Powered Chat

- Real-time WebSocket connections for live updates
- Message persistence in PostgreSQL
- LLM context enriched with knowledge base content
- Support for conversation history and multi-turn interactions

### 4. Proposal Generation

- LLM-based proposal creation using OpenAI API
- Configurable prompt templates
- Business context and history awareness

### 5. Authentication & Security

- JWT tokens via Supabase
- ES256 signed tokens with JWT secrets
- Role-based business access control
- Secure API key management

## Important Notes

### ⚠️ Database Initialization

- Tables are created automatically on first startup via `lifespan.py`
- pgvector extension is registered on each connection in `db.py`
- PostgreSQL must be running before the API starts

### ⚠️ Async/Await Throughout

- The entire codebase uses async/await patterns
- All database operations are async with AsyncSession
- Ensure any new code uses async context managers and awaits

### ⚠️ Celery Worker Requirement (Optional)

- Background tasks (document ingestion) are queued but not processed by the API
- To process background jobs, start a separate Celery worker:
  ```bash
  celery -A app.core.celery_app worker --loglevel=info
  ```
- Without a worker, tasks will queue up and not execute

### ⚠️ Environment Variables

- **Required**: `OPENAI_API_KEY`, all `SUPABASE_*` keys
- **Database**: `DB_URL` is auto-set in Docker to point to `postgres` service
- **Redis**: `REDIS_URL` is auto-set in Docker to point to `redis` service
- Missing env vars will cause startup failures

### 📝 Development Server

- FastAPI's development server includes Swagger UI at `/docs`
- Hot-reload is enabled for code changes
- Debug mode is recommended for local development

### 🔒 Database Credentials

- Default PostgreSQL user: `postgres`
- **Never commit `.env` files** with real credentials to version control
- Use `.env.example` template for team setup

## API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation.

### Main Endpoints

- `POST /api/v1/auth/login` — User authentication
- `POST /api/v1/auth/register` — User registration
- `GET /api/v1/business` — Get business details
- `POST /api/v1/knowledge-base` — Create knowledge base
- `POST /api/v1/knowledge-base/upload` — Upload document
- `POST /api/v1/chat/send` — Send chat message
- `WS /api/v1/chat/ws` — WebSocket chat connection

## Troubleshooting

### Docker Build Fails with `pg_config` Error

- Ensure `libpq-dev` is installed in Dockerfile.dev
- This provides PostgreSQL headers needed to compile `psycopg[c]`

### API Container Won't Start

- Check that PostgreSQL and Redis health checks pass: `docker-compose ps`
- View logs: `docker-compose logs api`
- Ensure `.env` file exists with required variables

### Embedding/Ingestion Tasks Don't Process

- Start a Celery worker: `celery -A app.core.celery_app worker --loglevel=info`
- Check Redis is running: `redis-cli ping` should return `PONG`

### Database Connection Refused

- Verify PostgreSQL is healthy: `docker-compose logs postgres`
- Check environment variables match `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

## Development Workflow

1. **Start services**: `docker-compose up`
2. **Monitor logs**: `docker-compose logs -f api`
3. **Edit code** — Changes auto-reload in development server
4. **Test endpoints** — Use http://localhost:8000/docs
5. **Stop services**: Press `Ctrl+C` or `docker-compose down`

## Contributing

- Follow async/await patterns for all I/O operations
- Use Pydantic models for request/response validation
- Add types to all functions (type hints enforcement recommended)
- Test with the interactive docs before committing

## License

Proprietary — Drafter Inc.
