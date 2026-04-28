# P1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the monorepo with a working FastAPI backend, arq worker, Next.js frontend (with Clerk auth), Postgres + Redis + MinIO via docker-compose, all data-model migrations, and CI green — so subsequent sub-projects (Credits, Pipeline, Publishing, …) build on a known-good foundation.

**Architecture:** Monorepo (pnpm workspaces). Two apps: `apps/api` (Python / FastAPI / arq / SQLAlchemy 2 / Alembic) and `apps/web` (Next.js 15 App Router / Clerk / TypeScript). Local dev via docker-compose for Postgres, Redis, and MinIO (R2 stand-in). CI runs lint + tests in GitHub Actions with Postgres as a service.

**Tech Stack:** Python 3.12, FastAPI 0.110+, SQLAlchemy 2.x, Alembic 1.13+, asyncpg, arq 0.25+, pydantic-settings, structlog, PyJWT (Clerk JWKS verification), cryptography (AES-GCM), pytest 8 + pytest-asyncio, Node 20, pnpm 9, Next.js 15 App Router, @clerk/nextjs 5.x, TypeScript 5.x.

**Spec reference:** `docs/superpowers/specs/2026-04-28-faceless-youtube-saas-design.md` (commit `e5438f0`).

---

## File Structure (locked at start of plan)

Files this plan creates. Subsequent sub-projects extend this structure rather than restructuring it.

```
faceless-yt/
├── .gitignore
├── .editorconfig
├── README.md
├── package.json                       # root, pnpm scripts
├── pnpm-workspace.yaml
├── docker-compose.yml                 # postgres, redis, minio
├── Makefile                           # convenience targets
├── .github/workflows/ci.yml
│
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   ├── script.py.mako
│   │   │   └── versions/0001_initial_schema.py
│   │   ├── src/faceless/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                # FastAPI app
│   │   │   ├── worker.py              # arq WorkerSettings
│   │   │   ├── config.py              # pydantic-settings
│   │   │   ├── crypto.py              # AES-GCM
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── deps.py            # current_user, db session
│   │   │   │   ├── errors.py          # error envelope + handlers
│   │   │   │   └── routes/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── health.py
│   │   │   │       └── me.py
│   │   │   ├── auth/
│   │   │   │   ├── __init__.py
│   │   │   │   └── clerk.py           # JWT verification via JWKS
│   │   │   ├── db/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py            # session factory, Base
│   │   │   │   └── models/
│   │   │   │       ├── __init__.py
│   │   │   │       └── user.py        # only User in P1; other models added in their sub-projects
│   │   │   └── observability/
│   │   │       ├── __init__.py
│   │   │       └── logging.py         # structlog setup
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── conftest.py
│   │       ├── unit/
│   │       │   ├── __init__.py
│   │       │   ├── test_crypto.py
│   │       │   ├── test_config.py
│   │       │   └── test_clerk_auth.py
│   │       └── integration/
│   │           ├── __init__.py
│   │           ├── test_health.py
│   │           ├── test_me.py
│   │           └── test_migrations.py
│   └── web/
│       ├── package.json
│       ├── next.config.ts
│       ├── tsconfig.json
│       ├── eslint.config.mjs
│       ├── postcss.config.mjs
│       ├── tailwind.config.ts
│       ├── .env.example
│       ├── middleware.ts              # Clerk middleware
│       └── src/
│           ├── app/
│           │   ├── layout.tsx
│           │   ├── page.tsx           # marketing landing
│           │   ├── globals.css
│           │   ├── sign-in/[[...sign-in]]/page.tsx
│           │   ├── sign-up/[[...sign-up]]/page.tsx
│           │   └── (app)/
│           │       └── dashboard/page.tsx
│           └── lib/
│               └── api-client.ts
└── packages/
    └── shared-types/
        ├── package.json
        ├── tsconfig.json
        └── src/index.ts
```

**Note on data-model scope:** The Alembic baseline migration creates **all** tables from spec §2 in one shot. ORM model classes are added per-sub-project as needed (P1 only adds `User`; P2 adds credit-related models; etc.). This keeps subsequent sub-projects free of schema migrations beyond minor additions.

---

## Task 1: Initialize monorepo & repo hygiene

**Files:**
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `.gitignore`
- Create: `.editorconfig`
- Create: `README.md`
- Create: `Makefile`

- [ ] **Step 1: Create `pnpm-workspace.yaml`**

```yaml
packages:
  - "apps/*"
  - "packages/*"
```

- [ ] **Step 2: Create root `package.json`**

```json
{
  "name": "faceless-yt",
  "private": true,
  "version": "0.0.0",
  "packageManager": "pnpm@9.12.0",
  "scripts": {
    "dev": "pnpm -r --parallel dev",
    "build": "pnpm -r build",
    "lint": "pnpm -r lint",
    "test": "pnpm -r test"
  },
  "devDependencies": {
    "typescript": "5.6.2"
  }
}
```

- [ ] **Step 3: Create `.gitignore`**

```gitignore
# Node
node_modules/
.next/
dist/
out/
*.log
.env
.env.local
.env.*.local

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
venv/
*.egg-info/

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Local data
.local/
postgres-data/
redis-data/
minio-data/
```

- [ ] **Step 4: Create `.editorconfig`**

```editorconfig
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.py]
indent_size = 4

[Makefile]
indent_style = tab
```

- [ ] **Step 5: Create `README.md`**

```markdown
# Faceless YT

Multi-tenant SaaS for AI-generated faceless YouTube channel automation.

## Local development

```bash
make dev      # Start postgres, redis, minio + watch all apps
make test     # Run all tests
make migrate  # Run Alembic migrations
```

See `docs/superpowers/specs/` for design.
```

- [ ] **Step 6: Create `Makefile`**

```makefile
.PHONY: dev down test migrate api-shell web-shell logs

dev:
	docker compose up -d postgres redis minio
	pnpm install
	pnpm -r --parallel dev

down:
	docker compose down

test:
	cd apps/api && pytest
	cd apps/web && pnpm test

migrate:
	cd apps/api && alembic upgrade head

api-shell:
	cd apps/api && python

web-shell:
	cd apps/web && pnpm exec tsc --noEmit

logs:
	docker compose logs -f
```

- [ ] **Step 7: Verify pnpm installs cleanly**

Run: `pnpm install`
Expected: workspace recognized, no errors. (Apps don't exist yet, so output is minimal.)

- [ ] **Step 8: Commit**

```bash
git add .gitignore .editorconfig README.md package.json pnpm-workspace.yaml Makefile
git commit -m "chore: initialize monorepo with pnpm workspaces"
```

---

## Task 2: Docker Compose for local dev (Postgres, Redis, MinIO)

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: faceless
      POSTGRES_PASSWORD: faceless
      POSTGRES_DB: faceless
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U faceless"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: faceless
      MINIO_ROOT_PASSWORD: facelessfaceless
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio-data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres-data:
  redis-data:
  minio-data:
```

- [ ] **Step 2: Bring up the stack**

Run: `docker compose up -d`
Expected: three containers running. Verify with `docker compose ps` — all show "healthy" or "running".

- [ ] **Step 3: Smoke-check Postgres connectivity**

Run: `docker compose exec postgres psql -U faceless -d faceless -c "SELECT 1;"`
Expected: `?column? = 1`.

- [ ] **Step 4: Smoke-check Redis**

Run: `docker compose exec redis redis-cli ping`
Expected: `PONG`.

- [ ] **Step 5: Smoke-check MinIO console**

Visit `http://localhost:9001`. Expected: MinIO login page (don't actually log in; just confirm it loads).

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml
git commit -m "chore: add docker-compose for postgres, redis, minio"
```

---

## Task 3: Bootstrap `apps/api` Python package

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/faceless/__init__.py`
- Create: `apps/api/tests/__init__.py`
- Create: `apps/api/tests/unit/__init__.py`
- Create: `apps/api/tests/integration/__init__.py`
- Create: `apps/api/.python-version`

- [ ] **Step 1: Create `apps/api/.python-version`**

```
3.12
```

- [ ] **Step 2: Create `apps/api/pyproject.toml`**

```toml
[project]
name = "faceless-api"
version = "0.0.0"
description = "Faceless YT backend"
requires-python = ">=3.12"
dependencies = [
    "fastapi==0.115.0",
    "uvicorn[standard]==0.30.6",
    "pydantic==2.9.2",
    "pydantic-settings==2.5.2",
    "sqlalchemy[asyncio]==2.0.35",
    "asyncpg==0.29.0",
    "alembic==1.13.3",
    "arq==0.26.1",
    "httpx==0.27.2",
    "PyJWT[crypto]==2.9.0",
    "cryptography==43.0.1",
    "structlog==24.4.0",
    "python-multipart==0.0.12",
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.3",
    "pytest-asyncio==0.24.0",
    "ruff==0.6.9",
    "mypy==1.11.2",
    "respx==0.21.1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/faceless"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM", "RUF"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short"
pythonpath = ["src"]
```

- [ ] **Step 3: Create empty package files**

```python
# apps/api/src/faceless/__init__.py
__version__ = "0.0.0"
```

```python
# apps/api/tests/__init__.py
```

```python
# apps/api/tests/unit/__init__.py
```

```python
# apps/api/tests/integration/__init__.py
```

- [ ] **Step 4: Create venv and install**

Run from `apps/api/`:
```bash
python -m venv .venv
.venv/Scripts/activate    # Windows
# OR: source .venv/bin/activate   # Unix
pip install -e ".[dev]"
```
Expected: install completes, all wheels resolve.

- [ ] **Step 5: Verify pytest runs**

Run from `apps/api/`: `pytest`
Expected: `no tests ran` (success, just no tests yet).

- [ ] **Step 6: Commit**

```bash
git add apps/api/pyproject.toml apps/api/.python-version apps/api/src apps/api/tests
git commit -m "chore(api): scaffold Python package with FastAPI/arq/SQLAlchemy"
```

---

## Task 4: Configuration via pydantic-settings

**Files:**
- Create: `apps/api/src/faceless/config.py`
- Create: `apps/api/tests/unit/test_config.py`

- [ ] **Step 1: Write failing test for config loading**

```python
# apps/api/tests/unit/test_config.py
import os
from faceless.config import Settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:y@h/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("S3_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("S3_ACCESS_KEY", "ak")
    monkeypatch.setenv("S3_SECRET_KEY", "sk")
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://example.clerk.accounts.dev")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "https://app.example.com")
    monkeypatch.setenv("ENCRYPTION_KEY", "0" * 44)  # 32 bytes base64

    settings = Settings()

    assert settings.database_url == "postgresql+asyncpg://x:y@h/db"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.s3_bucket == "test-bucket"
    assert settings.clerk_jwt_issuer == "https://example.clerk.accounts.dev"
    assert settings.log_level == "info"  # default
    assert settings.environment == "dev"  # default


def test_settings_missing_required_raises(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: faceless.config`.

- [ ] **Step 3: Implement `Settings`**

```python
# apps/api/src/faceless/config.py
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Required
    database_url: str = Field(..., description="Postgres async DSN")
    redis_url: str
    s3_bucket: str
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    clerk_jwt_issuer: str
    clerk_jwt_audience: str
    encryption_key: str = Field(..., description="Base64-encoded 32 bytes for AES-GCM")

    # Optional with defaults
    environment: Literal["dev", "staging", "prod"] = "dev"
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    s3_region: str = "auto"
    api_port: int = 8000
    cors_allow_origins: str = "http://localhost:3000"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_config.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Create `.env.example`**

```bash
# apps/api/.env.example
DATABASE_URL=postgresql+asyncpg://faceless:faceless@localhost:5432/faceless
REDIS_URL=redis://localhost:6379/0
S3_BUCKET=faceless-local
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=faceless
S3_SECRET_KEY=facelessfaceless
S3_REGION=auto

CLERK_JWT_ISSUER=https://example.clerk.accounts.dev
CLERK_JWT_AUDIENCE=https://app.example.com

# Generate with: python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
ENCRYPTION_KEY=PLACEHOLDER_REPLACE_ME

ENVIRONMENT=dev
LOG_LEVEL=info
```

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/faceless/config.py apps/api/tests/unit/test_config.py apps/api/.env.example
git commit -m "feat(api): pydantic-settings configuration"
```

---

## Task 5: Structured logging (structlog)

**Files:**
- Create: `apps/api/src/faceless/observability/__init__.py`
- Create: `apps/api/src/faceless/observability/logging.py`

- [ ] **Step 1: Create empty `observability/__init__.py`**

```python
# apps/api/src/faceless/observability/__init__.py
```

- [ ] **Step 2: Implement logging setup**

```python
# apps/api/src/faceless/observability/logging.py
import logging
import sys

import structlog

from faceless.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper())

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Quiet noisy libraries
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
```

- [ ] **Step 3: Smoke test manually**

Run from `apps/api/`:
```bash
python -c "from faceless.observability.logging import configure_logging, get_logger; configure_logging(); get_logger('test').info('hello', user='admin')"
```
Expected: one JSON log line on stdout with `event="hello"`, `user="admin"`, `level="info"`, `timestamp=...`.

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/faceless/observability
git commit -m "feat(api): structlog JSON logging"
```

---

## Task 6: AES-GCM encryption utility (for OAuth refresh tokens)

**Files:**
- Create: `apps/api/src/faceless/crypto.py`
- Create: `apps/api/tests/unit/test_crypto.py`

- [ ] **Step 1: Write failing test**

```python
# apps/api/tests/unit/test_crypto.py
import base64
import pytest
from faceless.crypto import encrypt, decrypt, InvalidCiphertext

KEY_B64 = base64.b64encode(b"\x00" * 32).decode()


def test_encrypt_decrypt_roundtrip():
    plaintext = "ya29.refresh-token-secret"
    ct = encrypt(plaintext, KEY_B64)
    assert ct != plaintext
    assert decrypt(ct, KEY_B64) == plaintext


def test_encrypt_produces_different_ciphertext_each_call():
    # AES-GCM uses a random nonce per call
    p = "same-plaintext"
    assert encrypt(p, KEY_B64) != encrypt(p, KEY_B64)


def test_decrypt_with_wrong_key_raises():
    other_key = base64.b64encode(b"\x01" * 32).decode()
    ct = encrypt("secret", KEY_B64)
    with pytest.raises(InvalidCiphertext):
        decrypt(ct, other_key)


def test_decrypt_tampered_ciphertext_raises():
    ct = encrypt("secret", KEY_B64)
    # Flip a byte in the middle
    raw = base64.b64decode(ct)
    tampered = raw[:20] + bytes([raw[20] ^ 0xFF]) + raw[21:]
    tampered_b64 = base64.b64encode(tampered).decode()
    with pytest.raises(InvalidCiphertext):
        decrypt(tampered_b64, KEY_B64)


def test_invalid_key_length_raises():
    short = base64.b64encode(b"\x00" * 16).decode()
    with pytest.raises(ValueError):
        encrypt("x", short)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_crypto.py -v`
Expected: FAIL with `ModuleNotFoundError: faceless.crypto`.

- [ ] **Step 3: Implement `crypto.py`**

```python
# apps/api/src/faceless/crypto.py
"""AES-GCM encryption for sensitive at-rest values (e.g., OAuth refresh tokens).

The key is a base64-encoded 32-byte secret loaded from `ENCRYPTION_KEY`.
Each call uses a fresh random 12-byte nonce, prepended to the ciphertext.
Output format (base64): nonce(12) || ciphertext || tag(16).
"""

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class InvalidCiphertext(Exception):
    """Raised when ciphertext is malformed, tampered, or decrypted with the wrong key."""


def _load_key(key_b64: str) -> bytes:
    raw = base64.b64decode(key_b64)
    if len(raw) != 32:
        raise ValueError(f"ENCRYPTION_KEY must decode to 32 bytes, got {len(raw)}")
    return raw


def encrypt(plaintext: str, key_b64: str) -> str:
    key = _load_key(key_b64)
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt(ciphertext_b64: str, key_b64: str) -> str:
    key = _load_key(key_b64)
    try:
        raw = base64.b64decode(ciphertext_b64)
    except (ValueError, base64.binascii.Error) as e:
        raise InvalidCiphertext("malformed base64") from e
    if len(raw) < 12 + 16:
        raise InvalidCiphertext("ciphertext too short")
    nonce, ct = raw[:12], raw[12:]
    aes = AESGCM(key)
    try:
        return aes.decrypt(nonce, ct, associated_data=None).decode("utf-8")
    except InvalidTag as e:
        raise InvalidCiphertext("authentication failed") from e
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_crypto.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/faceless/crypto.py apps/api/tests/unit/test_crypto.py
git commit -m "feat(api): AES-GCM encryption utility for sensitive at-rest values"
```

---

## Task 7: SQLAlchemy base + async session factory

**Files:**
- Create: `apps/api/src/faceless/db/__init__.py`
- Create: `apps/api/src/faceless/db/base.py`
- Create: `apps/api/src/faceless/db/models/__init__.py`

- [ ] **Step 1: Create empty `__init__.py` files**

```python
# apps/api/src/faceless/db/__init__.py
```

```python
# apps/api/src/faceless/db/models/__init__.py
```

- [ ] **Step 2: Implement `base.py`**

```python
# apps/api/src/faceless/db/base.py
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from faceless.config import get_settings


# Naming convention so Alembic generates stable, readable constraint names.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_settings().database_url,
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a session and rolls back on uncaught exceptions."""
    async with get_session_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 3: Smoke-check imports**

Run from `apps/api/`:
```bash
python -c "from faceless.db.base import Base, get_db_session; print('ok')"
```
Expected: `ok` printed (no DB connection attempted yet — connection is lazy).

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/faceless/db
git commit -m "feat(api): SQLAlchemy 2 async base, session factory, naming convention"
```

---

## Task 8: User ORM model

**Files:**
- Create: `apps/api/src/faceless/db/models/user.py`

- [ ] **Step 1: Implement `User` model**

```python
# apps/api/src/faceless/db/models/user.py
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from faceless.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass  # other relationships added in later sub-projects


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    clerk_user_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    credit_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email!r}>"
```

- [ ] **Step 2: Update `db/models/__init__.py` to re-export**

```python
# apps/api/src/faceless/db/models/__init__.py
from faceless.db.models.user import User

__all__ = ["User"]
```

- [ ] **Step 3: Smoke-check import**

Run: `python -c "from faceless.db.models import User; print(User.__tablename__)"`
Expected: `users`.

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/faceless/db/models
git commit -m "feat(api): User ORM model"
```

---

## Task 9: Alembic baseline migration (all spec tables)

This task creates one migration that creates **every table** from the spec. Future sub-projects add ORM model classes incrementally; the schema is already in place.

**Files:**
- Create: `apps/api/alembic.ini`
- Create: `apps/api/alembic/env.py`
- Create: `apps/api/alembic/script.py.mako`
- Create: `apps/api/alembic/versions/0001_initial_schema.py`

- [ ] **Step 1: Initialize Alembic**

Run from `apps/api/`: `alembic init alembic`
Expected: creates `alembic/`, `alembic.ini`. Do NOT commit yet — we'll edit them.

- [ ] **Step 2: Replace `apps/api/alembic.ini`**

Replace the generated content with:

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://faceless:faceless@localhost:5432/faceless
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s
prepend_sys_path = src
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: Replace `apps/api/alembic/env.py`**

```python
# apps/api/alembic/env.py
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from faceless.config import get_settings
from faceless.db.base import Base
from faceless.db import models  # noqa: F401  (registers all models)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Create the baseline migration**

Replace any auto-generated file in `apps/api/alembic/versions/` with this single file:

```python
# apps/api/alembic/versions/0001_initial_schema.py
"""initial schema covering all spec tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-28
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("clerk_user_id", sa.String(128), nullable=False),
        sa.Column("credit_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("clerk_user_id", name="uq_users_clerk_user_id"),
    )

    # channels
    op.create_table(
        "channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("youtube_channel_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("handle", sa.String(64), nullable=True),
        sa.Column("oauth_refresh_token", sa.Text(), nullable=False),
        sa.Column("oauth_access_token", sa.Text(), nullable=True),
        sa.Column("oauth_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_channels_user_id", "channels", ["user_id"])

    # learning_profiles (referenced by content_series)
    op.create_table(
        "learning_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("top_performers_job_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("negative_signal_job_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("aggregate_features_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("last_recomputed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("channel_id", name="uq_learning_profiles_channel_id"),
    )

    # content_series
    op.create_table(
        "content_series",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("niche", sa.String(255), nullable=True),
        sa.Column("target_format", sa.String(16), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("cadence_cron", sa.String(64), nullable=False),
        sa.Column("auto_approve_after_hours", sa.Integer(), nullable=True),
        sa.Column("voice_id", sa.String(64), nullable=False),
        sa.Column("music_mood", sa.String(64), nullable=False),
        sa.Column("style_preset", sa.String(64), nullable=False),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("learning_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learning_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("target_format in ('short','long')", name="ck_content_series_target_format"),
    )
    op.create_index(
        "ix_content_series_next_run_at_active",
        "content_series", ["next_run_at"],
        postgresql_where=sa.text("paused_at IS NULL"),
    )

    # jobs
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("series_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_series.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("format", sa.String(16), nullable=False),
        sa.Column("credit_cost", sa.Integer(), nullable=False),
        sa.Column("prompt_resolved", sa.Text(), nullable=True),
        sa.Column("script_text", sa.Text(), nullable=True),
        sa.Column("script_metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("scene_plan_json", postgresql.JSONB(), nullable=True),
        sa.Column("final_video_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("final_thumbnail_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_detail", postgresql.JSONB(), nullable=True),
        sa.Column("current_stage_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("state_changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_jobs_state_state_changed_at", "jobs", ["state", "state_changed_at"])
    op.create_index("ix_jobs_user_id_created_at", "jobs", ["user_id", sa.text("created_at DESC")])

    # assets
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("s3_key", sa.String(512), nullable=False),
        sa.Column("mime", sa.String(64), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_assets_job_id", "assets", ["job_id"])

    # add the deferred foreign keys on jobs.final_*_asset_id now that assets exists
    op.create_foreign_key(
        "fk_jobs_final_video_asset_id_assets", "jobs", "assets",
        ["final_video_asset_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_jobs_final_thumbnail_asset_id_assets", "jobs", "assets",
        ["final_thumbnail_asset_id"], ["id"], ondelete="SET NULL",
    )

    # scenes
    op.create_table(
        "scenes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("image_prompt", sa.Text(), nullable=False),
        sa.Column("narration_text", sa.Text(), nullable=False),
        sa.Column("image_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("clip_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("audio_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kling_external_job_id", sa.String(128), nullable=True),
        sa.Column("visual_state", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("audio_state", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("image_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clip_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("audio_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_scenes_job_id_idx", "scenes", ["job_id", "idx"])

    # credit_transactions
    op.create_table(
        "credit_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_credit_transactions_user_id_created_at",
                    "credit_transactions", ["user_id", sa.text("created_at DESC")])
    op.create_index(
        "ix_credit_transactions_stripe_payment_intent_id",
        "credit_transactions", ["stripe_payment_intent_id"],
        unique=True, postgresql_where=sa.text("stripe_payment_intent_id IS NOT NULL"),
    )
    op.create_index(
        "uq_credit_transactions_job_refund",
        "credit_transactions", ["job_id"],
        unique=True, postgresql_where=sa.text("reason = 'job_refund'"),
    )

    # approval_events
    op.create_table(
        "approval_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # published_videos
    op.create_table(
        "published_videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("youtube_video_id", sa.String(32), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_analytics_pull_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_analytics_pull_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("job_id", name="uq_published_videos_job_id"),
        sa.UniqueConstraint("youtube_video_id", name="uq_published_videos_youtube_video_id"),
    )
    op.create_index(
        "ix_published_videos_next_analytics_pull_at",
        "published_videos", ["next_analytics_pull_at"],
        postgresql_where=sa.text("next_analytics_pull_at IS NOT NULL"),
    )

    # analytics_snapshots
    op.create_table(
        "analytics_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("published_video_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("published_videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pulled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("views", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("watch_time_minutes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("avg_view_duration_s", sa.Float(), nullable=True),
        sa.Column("ctr_pct", sa.Float(), nullable=True),
        sa.Column("likes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("comments", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("subs_gained", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_index("ix_analytics_snapshots_published_video_id_pulled_at",
                    "analytics_snapshots", ["published_video_id", "pulled_at"])

    # unit_costs
    op.create_table(
        "unit_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("units", sa.Float(), nullable=False),
        sa.Column("usd_cost", sa.Numeric(10, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # job_events (audit trail)
    op.create_table(
        "job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_state", sa.String(32), nullable=True),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("worker_id", sa.String(64), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_detail", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_job_events_job_id_at", "job_events", ["job_id", "at"])

    # credit_packs (config table)
    op.create_table(
        "credit_packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("price_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("stripe_price_id", sa.String(128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # video_pricing (config table)
    op.create_table(
        "video_pricing",
        sa.Column("format", sa.String(16), primary_key=True),
        sa.Column("credits", sa.Integer(), nullable=False),
    )

    # promo_codes
    op.create_table(
        "promo_codes",
        sa.Column("code", sa.String(64), primary_key=True),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("single_use", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "promo_redemptions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("code", sa.String(64), sa.ForeignKey("promo_codes.code", ondelete="CASCADE"), primary_key=True),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("promo_redemptions")
    op.drop_table("promo_codes")
    op.drop_table("video_pricing")
    op.drop_table("credit_packs")
    op.drop_index("ix_job_events_job_id_at", table_name="job_events")
    op.drop_table("job_events")
    op.drop_table("unit_costs")
    op.drop_index("ix_analytics_snapshots_published_video_id_pulled_at", table_name="analytics_snapshots")
    op.drop_table("analytics_snapshots")
    op.drop_index("ix_published_videos_next_analytics_pull_at", table_name="published_videos")
    op.drop_table("published_videos")
    op.drop_table("approval_events")
    op.drop_index("uq_credit_transactions_job_refund", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_stripe_payment_intent_id", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_user_id_created_at", table_name="credit_transactions")
    op.drop_table("credit_transactions")
    op.drop_index("ix_scenes_job_id_idx", table_name="scenes")
    op.drop_table("scenes")
    op.drop_constraint("fk_jobs_final_thumbnail_asset_id_assets", "jobs", type_="foreignkey")
    op.drop_constraint("fk_jobs_final_video_asset_id_assets", "jobs", type_="foreignkey")
    op.drop_index("ix_assets_job_id", table_name="assets")
    op.drop_table("assets")
    op.drop_index("ix_jobs_user_id_created_at", table_name="jobs")
    op.drop_index("ix_jobs_state_state_changed_at", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_content_series_next_run_at_active", table_name="content_series")
    op.drop_table("content_series")
    op.drop_table("learning_profiles")
    op.drop_index("ix_channels_user_id", table_name="channels")
    op.drop_table("channels")
    op.drop_table("users")
```

- [ ] **Step 5: Run migration against local Postgres**

Ensure docker-compose Postgres is up. From `apps/api/`, with venv active and a `.env` populated:
```bash
alembic upgrade head
```
Expected: `Running upgrade  -> 0001_initial, initial schema covering all spec tables`.

- [ ] **Step 6: Verify schema**

```bash
docker compose exec postgres psql -U faceless -d faceless -c "\dt"
```
Expected: lists all tables (users, channels, content_series, jobs, scenes, assets, credit_transactions, approval_events, published_videos, analytics_snapshots, unit_costs, job_events, credit_packs, video_pricing, promo_codes, promo_redemptions, alembic_version).

- [ ] **Step 7: Round-trip test (downgrade then upgrade)**

```bash
alembic downgrade base && alembic upgrade head
```
Expected: both succeed without error.

- [ ] **Step 8: Commit**

```bash
git add apps/api/alembic.ini apps/api/alembic
git commit -m "feat(api): Alembic baseline migration covering all spec tables"
```

---

## Task 10: Integration test for migrations + User insert

**Files:**
- Create: `apps/api/tests/conftest.py`
- Create: `apps/api/tests/integration/test_migrations.py`

- [ ] **Step 1: Write `conftest.py`**

```python
# apps/api/tests/conftest.py
import asyncio
import os
import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure required env vars exist for tests; CI provides real values.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://faceless:faceless@localhost:5432/faceless_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("S3_BUCKET", "test-bucket")
os.environ.setdefault("S3_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "ak")
os.environ.setdefault("S3_SECRET_KEY", "sk")
os.environ.setdefault("CLERK_JWT_ISSUER", "https://test.clerk.accounts.dev")
os.environ.setdefault("CLERK_JWT_AUDIENCE", "https://app.test")
os.environ.setdefault("ENCRYPTION_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_engine():
    """Create the test DB schema via Alembic, yield engine, drop schema."""
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

    # Create the test database if missing
    admin_url = os.environ["DATABASE_URL"].rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(__import__("sqlalchemy").text(
            "DROP DATABASE IF EXISTS faceless_test"
        ))
        await conn.execute(__import__("sqlalchemy").text(
            "CREATE DATABASE faceless_test"
        ))
    await admin_engine.dispose()

    # Run migrations
    command.upgrade(cfg, "head")

    engine = create_async_engine(os.environ["DATABASE_URL"])
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
```

- [ ] **Step 2: Write integration test**

```python
# apps/api/tests/integration/test_migrations.py
import uuid

import pytest
from sqlalchemy import select

from faceless.db.models import User


@pytest.mark.asyncio
async def test_can_insert_and_select_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="alice@example.com",
        clerk_user_id="user_alice",
        credit_balance=0,
    )
    db_session.add(user)
    await db_session.flush()

    result = await db_session.execute(select(User).where(User.email == "alice@example.com"))
    found = result.scalar_one()
    assert found.id == user.id
    assert found.credit_balance == 0
```

- [ ] **Step 3: Run integration test**

Ensure docker-compose Postgres is up. From `apps/api/`:
```bash
pytest tests/integration/test_migrations.py -v
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/api/tests/conftest.py apps/api/tests/integration/test_migrations.py
git commit -m "test(api): integration test for migrations + User insert"
```

---

## Task 11: Clerk JWT verification

**Files:**
- Create: `apps/api/src/faceless/auth/__init__.py`
- Create: `apps/api/src/faceless/auth/clerk.py`
- Create: `apps/api/tests/unit/test_clerk_auth.py`

- [ ] **Step 1: Empty `__init__.py`**

```python
# apps/api/src/faceless/auth/__init__.py
```

- [ ] **Step 2: Write failing test**

```python
# apps/api/tests/unit/test_clerk_auth.py
import time

import jwt
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import Response

from faceless.auth.clerk import (
    ClerkClaims,
    InvalidToken,
    verify_clerk_token,
    _jwks_cache_clear,
)


@pytest.fixture
def rsa_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = key.public_key()
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    priv_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    # JWK form
    nums = pub.public_numbers()
    import base64
    def b64(n: int) -> str:
        b = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    jwk = {
        "kid": "test-kid",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "n": b64(nums.n),
        "e": b64(nums.e),
    }
    return priv_pem, pub_pem, jwk


def make_token(priv_pem: bytes, *, sub="user_x", iss="https://test.clerk.accounts.dev",
               aud="https://app.test", exp_offset=60, kid="test-kid") -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": sub, "iss": iss, "aud": aud, "iat": now, "exp": now + exp_offset, "email": "x@y.com"},
        priv_pem,
        algorithm="RS256",
        headers={"kid": kid},
    )


@pytest.mark.asyncio
async def test_verify_valid_token(rsa_keypair):
    priv, _pub, jwk = rsa_keypair
    _jwks_cache_clear()
    with respx.mock:
        respx.get("https://test.clerk.accounts.dev/.well-known/jwks.json").mock(
            return_value=Response(200, json={"keys": [jwk]})
        )
        token = make_token(priv)
        claims = await verify_clerk_token(token)
        assert isinstance(claims, ClerkClaims)
        assert claims.sub == "user_x"
        assert claims.email == "x@y.com"


@pytest.mark.asyncio
async def test_expired_token_rejected(rsa_keypair):
    priv, _, jwk = rsa_keypair
    _jwks_cache_clear()
    with respx.mock:
        respx.get("https://test.clerk.accounts.dev/.well-known/jwks.json").mock(
            return_value=Response(200, json={"keys": [jwk]})
        )
        token = make_token(priv, exp_offset=-10)
        with pytest.raises(InvalidToken):
            await verify_clerk_token(token)


@pytest.mark.asyncio
async def test_wrong_audience_rejected(rsa_keypair):
    priv, _, jwk = rsa_keypair
    _jwks_cache_clear()
    with respx.mock:
        respx.get("https://test.clerk.accounts.dev/.well-known/jwks.json").mock(
            return_value=Response(200, json={"keys": [jwk]})
        )
        token = make_token(priv, aud="https://wrong.example.com")
        with pytest.raises(InvalidToken):
            await verify_clerk_token(token)


@pytest.mark.asyncio
async def test_unknown_kid_rejected(rsa_keypair):
    priv, _, jwk = rsa_keypair
    _jwks_cache_clear()
    with respx.mock:
        respx.get("https://test.clerk.accounts.dev/.well-known/jwks.json").mock(
            return_value=Response(200, json={"keys": [jwk]})
        )
        token = make_token(priv, kid="unknown-kid")
        with pytest.raises(InvalidToken):
            await verify_clerk_token(token)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_clerk_auth.py -v`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement `clerk.py`**

```python
# apps/api/src/faceless/auth/clerk.py
"""Clerk JWT verification via the public JWKS endpoint.

Tokens are RS256-signed; public keys are fetched from
`{issuer}/.well-known/jwks.json` and cached in-process for 10 minutes.
"""

import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from faceless.config import get_settings


class InvalidToken(Exception):
    """Raised when the JWT is malformed, expired, has wrong audience, or fails signature."""


@dataclass(frozen=True)
class ClerkClaims:
    sub: str  # Clerk user id
    email: str | None
    raw: dict[str, Any]


_JWKS_TTL_S = 600
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _jwks_cache_clear() -> None:
    """Test helper — clear the JWKS cache."""
    _jwks_cache.clear()


async def _fetch_jwks(issuer: str) -> dict[str, Any]:
    cached = _jwks_cache.get(issuer)
    if cached and cached[0] > time.time():
        return cached[1]
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{issuer.rstrip('/')}/.well-known/jwks.json")
        resp.raise_for_status()
        jwks = resp.json()
    _jwks_cache[issuer] = (time.time() + _JWKS_TTL_S, jwks)
    return jwks


def _key_for_kid(jwks: dict[str, Any], kid: str):
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return RSAAlgorithm.from_jwk(key)
    raise InvalidToken(f"unknown kid: {kid}")


async def verify_clerk_token(token: str) -> ClerkClaims:
    settings = get_settings()
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as e:
        raise InvalidToken("malformed token") from e

    kid = unverified_header.get("kid")
    if not kid:
        raise InvalidToken("missing kid")

    jwks = await _fetch_jwks(settings.clerk_jwt_issuer)
    public_key = _key_for_kid(jwks, kid)

    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.clerk_jwt_audience,
            issuer=settings.clerk_jwt_issuer,
        )
    except jwt.ExpiredSignatureError as e:
        raise InvalidToken("expired") from e
    except jwt.InvalidTokenError as e:
        raise InvalidToken(str(e)) from e

    sub = claims.get("sub")
    if not sub:
        raise InvalidToken("missing sub claim")

    return ClerkClaims(sub=sub, email=claims.get("email"), raw=claims)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_clerk_auth.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/faceless/auth apps/api/tests/unit/test_clerk_auth.py
git commit -m "feat(api): Clerk JWT verification via JWKS"
```

---

## Task 12: Error envelope + handlers

**Files:**
- Create: `apps/api/src/faceless/api/__init__.py`
- Create: `apps/api/src/faceless/api/errors.py`

- [ ] **Step 1: Empty `__init__.py`**

```python
# apps/api/src/faceless/api/__init__.py
```

- [ ] **Step 2: Implement `errors.py`**

```python
# apps/api/src/faceless/api/errors.py
"""Standardized error envelope: { "error": { "code", "message", "detail" } }."""

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Base class for application-level errors that map to a JSON envelope."""

    code: str = "internal_error"
    status_code: int = 500
    message: str = "An internal error occurred."

    def __init__(self, message: str | None = None, detail: dict[str, Any] | None = None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.detail = detail or {}


class UnauthorizedError(AppError):
    code = "unauthorized"
    status_code = 401
    message = "Authentication required."


class ForbiddenError(AppError):
    code = "forbidden"
    status_code = 403
    message = "You do not have access to this resource."


class NotFoundError(AppError):
    code = "not_found"
    status_code = 404
    message = "Resource not found."


def _envelope(code: str, message: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "detail": detail or {}}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_req: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.detail),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_req: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope("http_error", str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_req: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_envelope("validation_error", "Invalid request payload.", {"errors": exc.errors()}),
        )
```

- [ ] **Step 3: Commit**

```bash
git add apps/api/src/faceless/api/__init__.py apps/api/src/faceless/api/errors.py
git commit -m "feat(api): standardized error envelope and handlers"
```

---

## Task 13: `current_user` dependency + DB session dep

**Files:**
- Create: `apps/api/src/faceless/api/deps.py`

- [ ] **Step 1: Implement `deps.py`**

```python
# apps/api/src/faceless/api/deps.py
"""FastAPI dependencies: DB session, current user from Clerk JWT."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from faceless.api.errors import UnauthorizedError
from faceless.auth.clerk import ClerkClaims, InvalidToken, verify_clerk_token
from faceless.db.base import get_db_session
from faceless.db.models import User


async def db_session_dep() -> AsyncIterator[AsyncSession]:
    async for s in get_db_session():
        yield s


DbSession = Annotated[AsyncSession, Depends(db_session_dep)]


async def _claims_from_header(authorization: str | None) -> ClerkClaims:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return await verify_clerk_token(token)
    except InvalidToken as e:
        raise UnauthorizedError(f"Invalid token: {e}") from e


async def current_user(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Resolve (or auto-create) the User row for a verified Clerk session."""
    claims = await _claims_from_header(authorization)

    result = await db.execute(select(User).where(User.clerk_user_id == claims.sub))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            clerk_user_id=claims.sub,
            email=claims.email or f"{claims.sub}@unknown.local",
            credit_balance=0,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


CurrentUser = Annotated[User, Depends(current_user)]
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/src/faceless/api/deps.py
git commit -m "feat(api): current_user and db_session FastAPI dependencies"
```

---

## Task 14: Health endpoint

**Files:**
- Create: `apps/api/src/faceless/api/routes/__init__.py`
- Create: `apps/api/src/faceless/api/routes/health.py`
- Create: `apps/api/tests/integration/test_health.py`

- [ ] **Step 1: Empty `__init__.py`**

```python
# apps/api/src/faceless/api/routes/__init__.py
```

- [ ] **Step 2: Write failing test**

```python
# apps/api/tests/integration/test_health.py
import pytest
from httpx import ASGITransport, AsyncClient

from faceless.main import create_app


@pytest.mark.asyncio
async def test_health_returns_ok():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "version" in body
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/integration/test_health.py -v`
Expected: FAIL — `faceless.main.create_app` not found yet (Task 15 wires it up).

- [ ] **Step 4: Implement health route**

```python
# apps/api/src/faceless/api/routes/health.py
from fastapi import APIRouter

from faceless import __version__

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
```

- [ ] **Step 5: Commit (test stays failing until Task 15 wires the app)**

```bash
git add apps/api/src/faceless/api/routes apps/api/tests/integration/test_health.py
git commit -m "feat(api): health endpoint (test pending app wiring)"
```

---

## Task 15: `/me` endpoint + FastAPI app wiring

**Files:**
- Create: `apps/api/src/faceless/api/routes/me.py`
- Create: `apps/api/src/faceless/main.py`
- Create: `apps/api/tests/integration/test_me.py`

- [ ] **Step 1: Implement `me.py`**

```python
# apps/api/src/faceless/api/routes/me.py
import uuid

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from faceless.api.deps import CurrentUser

router = APIRouter(prefix="/me", tags=["me"])


class MeResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    credit_balance: int


@router.get("", response_model=MeResponse)
async def get_me(user: CurrentUser) -> MeResponse:
    return MeResponse(id=user.id, email=user.email, credit_balance=user.credit_balance)
```

- [ ] **Step 2: Implement `main.py`**

```python
# apps/api/src/faceless/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from faceless import __version__
from faceless.api.errors import register_exception_handlers
from faceless.api.routes import health, me
from faceless.config import get_settings
from faceless.observability.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(
        title="Faceless YT API",
        version=__version__,
        docs_url="/api/docs" if settings.environment != "prod" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    api_v1 = "/api/v1"
    app.include_router(health.router, prefix=api_v1)
    app.include_router(me.router, prefix=api_v1)

    return app


app = create_app()
```

- [ ] **Step 3: Write `/me` integration test (mocks Clerk JWKS)**

```python
# apps/api/tests/integration/test_me.py
import time

import jwt
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient, Response

from faceless.auth.clerk import _jwks_cache_clear
from faceless.main import create_app


@pytest.fixture
def signing_setup():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_nums = key.public_key().public_numbers()
    import base64
    def b64(n: int) -> str:
        b = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    jwk = {"kid": "kid-test", "kty": "RSA", "alg": "RS256", "use": "sig",
           "n": b64(pub_nums.n), "e": b64(pub_nums.e)}
    priv_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return priv_pem, jwk


def _make_token(priv_pem: bytes, *, sub: str, email: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": sub, "iss": "https://test.clerk.accounts.dev", "aud": "https://app.test",
         "iat": now, "exp": now + 60, "email": email},
        priv_pem,
        algorithm="RS256",
        headers={"kid": "kid-test"},
    )


@pytest.mark.asyncio
async def test_me_creates_and_returns_user(db_engine, signing_setup):
    priv, jwk = signing_setup
    _jwks_cache_clear()
    app = create_app()

    with respx.mock(assert_all_called=False):
        respx.get("https://test.clerk.accounts.dev/.well-known/jwks.json").mock(
            return_value=Response(200, json={"keys": [jwk]})
        )
        token = _make_token(priv, sub="user_first", email="first@example.com")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/me", headers={"authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            body = resp.json()
            assert body["email"] == "first@example.com"
            assert body["credit_balance"] == 0
            first_id = body["id"]

            # Same Clerk sub → same user
            resp2 = await client.get("/api/v1/me", headers={"authorization": f"Bearer {token}"})
            assert resp2.json()["id"] == first_id


@pytest.mark.asyncio
async def test_me_rejects_missing_token():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/me")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_me_rejects_invalid_token():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/me", headers={"authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401
```

- [ ] **Step 4: Run all integration tests**

Ensure docker-compose Postgres is up and `faceless_test` DB will be created by conftest. From `apps/api/`:
```bash
pytest tests/integration -v
```
Expected: `test_health_returns_ok`, `test_me_creates_and_returns_user`, `test_me_rejects_missing_token`, `test_me_rejects_invalid_token` all PASS. `test_can_insert_and_select_user` from Task 10 still PASSes.

- [ ] **Step 5: Smoke-run the API server manually**

From `apps/api/`:
```bash
uvicorn faceless.main:app --reload --port 8000
```
Visit `http://localhost:8000/api/v1/health` — expect `{"status":"ok","version":"0.0.0"}`.
Visit `http://localhost:8000/api/docs` — expect Swagger UI.

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/faceless/api/routes/me.py apps/api/src/faceless/main.py apps/api/tests/integration/test_me.py
git commit -m "feat(api): /me endpoint with Clerk auth + FastAPI app wiring"
```

---

## Task 16: arq worker skeleton with hello-world task

**Files:**
- Create: `apps/api/src/faceless/worker.py`
- Create: `apps/api/tests/integration/test_worker.py`

- [ ] **Step 1: Implement `worker.py`**

```python
# apps/api/src/faceless/worker.py
"""arq worker entry point.

Pipeline stage handlers are added in their respective sub-projects (P3+).
For P1, this file establishes the WorkerSettings and a hello-world task
to verify the worker can run end-to-end.
"""

from typing import Any

from arq.connections import RedisSettings
from arq.worker import Worker

from faceless.config import get_settings
from faceless.observability.logging import configure_logging, get_logger

log = get_logger("worker")


async def hello(ctx: dict[str, Any], name: str) -> str:
    log.info("hello.start", name=name)
    return f"hello, {name}"


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    log.info("worker.startup")


async def shutdown(ctx: dict[str, Any]) -> None:
    log.info("worker.shutdown")


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    redis_settings = _redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    functions = [hello]
    cron_jobs: list[Any] = []  # populated in later sub-projects
    max_jobs = 10
    job_timeout = 30 * 60  # 30 min — accommodates Kling polling later
```

- [ ] **Step 2: Write integration test**

```python
# apps/api/tests/integration/test_worker.py
import asyncio
import pytest
from arq import create_pool

from faceless.config import get_settings
from faceless.worker import WorkerSettings


@pytest.mark.asyncio
async def test_can_enqueue_and_run_hello_task():
    pool = await create_pool(WorkerSettings.redis_settings)
    try:
        # Clear any leftover queue state from prior runs
        await pool.flushdb()
        job = await pool.enqueue_job("hello", "world")
        assert job is not None

        # Spin up an in-process worker for one job
        from arq.worker import Worker
        worker = Worker(
            functions=WorkerSettings.functions,
            redis_settings=WorkerSettings.redis_settings,
            on_startup=WorkerSettings.on_startup,
            on_shutdown=WorkerSettings.on_shutdown,
            burst=True,
            poll_delay=0.1,
        )
        await worker.async_run()

        result = await job.result(timeout=5)
        assert result == "hello, world"
    finally:
        await pool.close()
```

- [ ] **Step 3: Run test**

Ensure docker-compose Redis is up. From `apps/api/`:
```bash
pytest tests/integration/test_worker.py -v
```
Expected: PASS, with worker startup/shutdown logs printed.

- [ ] **Step 4: Smoke-run the worker manually**

From `apps/api/`:
```bash
arq faceless.worker.WorkerSettings
```
Expected: worker starts, logs `worker.startup`, idles waiting for jobs. Ctrl+C to stop.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/faceless/worker.py apps/api/tests/integration/test_worker.py
git commit -m "feat(api): arq worker skeleton with hello-world task"
```

---

## Task 17: Bootstrap `apps/web` (Next.js 15 + TypeScript + Tailwind)

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/eslint.config.mjs`
- Create: `apps/web/postcss.config.mjs`
- Create: `apps/web/tailwind.config.ts`
- Create: `apps/web/.env.example`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/app/globals.css`

- [ ] **Step 1: Create `apps/web/package.json`**

```json
{
  "name": "@faceless-yt/web",
  "version": "0.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "next lint",
    "test": "echo \"(no web tests in P1)\" && exit 0",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@clerk/nextjs": "5.7.5",
    "next": "15.0.2",
    "react": "19.0.0-rc-02c0e824-20241028",
    "react-dom": "19.0.0-rc-02c0e824-20241028"
  },
  "devDependencies": {
    "@types/node": "22.7.7",
    "@types/react": "18.3.12",
    "@types/react-dom": "18.3.1",
    "autoprefixer": "10.4.20",
    "eslint": "9.13.0",
    "eslint-config-next": "15.0.2",
    "postcss": "8.4.47",
    "tailwindcss": "3.4.14",
    "typescript": "5.6.3"
  }
}
```

- [ ] **Step 2: Create `apps/web/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Create `apps/web/next.config.ts`**

```ts
import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  experimental: { typedRoutes: true },
};

export default config;
```

- [ ] **Step 4: Create `apps/web/eslint.config.mjs`**

```js
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });
const eslintConfig = [...compat.extends("next/core-web-vitals", "next/typescript")];
export default eslintConfig;
```

- [ ] **Step 5: Create `apps/web/postcss.config.mjs`**

```js
export default { plugins: { tailwindcss: {}, autoprefixer: {} } };
```

- [ ] **Step 6: Create `apps/web/tailwind.config.ts`**

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
};

export default config;
```

- [ ] **Step 7: Create `apps/web/.env.example`**

```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_REPLACE_ME
CLERK_SECRET_KEY=sk_test_REPLACE_ME
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

- [ ] **Step 8: Create `apps/web/src/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body { height: 100%; }
body { @apply bg-white text-neutral-900; }
```

- [ ] **Step 9: Create `apps/web/src/app/layout.tsx`** (Clerk provider wired here)

```tsx
import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

export const metadata: Metadata = {
  title: "Faceless YT",
  description: "AI-generated faceless YouTube channel automation.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>{children}</body>
      </html>
    </ClerkProvider>
  );
}
```

- [ ] **Step 10: Create `apps/web/src/app/page.tsx`**

```tsx
import Link from "next/link";

export default function MarketingHome() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-24 text-center">
      <h1 className="text-5xl font-bold tracking-tight">Faceless YT</h1>
      <p className="mt-4 text-lg text-neutral-600">
        AI-generated faceless YouTube channel automation.
      </p>
      <div className="mt-8 flex justify-center gap-4">
        <Link href="/sign-in" className="rounded bg-neutral-900 px-4 py-2 text-white">
          Sign in
        </Link>
        <Link href="/sign-up" className="rounded border border-neutral-300 px-4 py-2">
          Sign up
        </Link>
      </div>
    </main>
  );
}
```

- [ ] **Step 11: Install web deps**

From repo root: `pnpm install`
Expected: pnpm resolves and installs without errors.

- [ ] **Step 12: Verify type-check passes**

Run from `apps/web/`: `pnpm typecheck`
Expected: no output (success).

- [ ] **Step 13: Verify dev server starts**

From `apps/web/`: `pnpm dev`
Visit `http://localhost:3000` — expect the marketing page rendered. Ctrl+C to stop. (Clerk will warn about missing keys; that's fine without real keys.)

- [ ] **Step 14: Commit**

```bash
git add apps/web
git commit -m "feat(web): scaffold Next.js 15 with Clerk provider and Tailwind"
```

---

## Task 18: Clerk middleware + protected dashboard skeleton

**Files:**
- Create: `apps/web/middleware.ts`
- Create: `apps/web/src/app/sign-in/[[...sign-in]]/page.tsx`
- Create: `apps/web/src/app/sign-up/[[...sign-up]]/page.tsx`
- Create: `apps/web/src/app/(app)/dashboard/page.tsx`

- [ ] **Step 1: Create `apps/web/middleware.ts`**

```ts
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isProtectedRoute = createRouteMatcher([
  "/dashboard(.*)",
  "/channels(.*)",
  "/series(.*)",
  "/queue(.*)",
  "/jobs(.*)",
  "/published(.*)",
  "/billing(.*)",
  "/settings(.*)",
]);

export default clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)", "/(api|trpc)(.*)"],
};
```

- [ ] **Step 2: Create `apps/web/src/app/sign-in/[[...sign-in]]/page.tsx`**

```tsx
import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <main className="flex min-h-screen items-center justify-center">
      <SignIn />
    </main>
  );
}
```

- [ ] **Step 3: Create `apps/web/src/app/sign-up/[[...sign-up]]/page.tsx`**

```tsx
import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <main className="flex min-h-screen items-center justify-center">
      <SignUp />
    </main>
  );
}
```

- [ ] **Step 4: Create `apps/web/src/app/(app)/dashboard/page.tsx`**

```tsx
import { auth } from "@clerk/nextjs/server";
import { UserButton } from "@clerk/nextjs";

export default async function DashboardPage() {
  const { userId } = await auth();

  return (
    <main className="mx-auto max-w-5xl p-8">
      <header className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <UserButton />
      </header>
      <p className="text-neutral-600">
        Signed in as <code className="text-sm">{userId}</code>.
      </p>
      <p className="mt-2 text-neutral-500">
        Connect a YouTube channel and create a content series to get started.
        (Coming in P4.)
      </p>
    </main>
  );
}
```

- [ ] **Step 5: Type-check & smoke-run**

From `apps/web/`:
```bash
pnpm typecheck
pnpm dev
```
With real Clerk dev keys in `.env.local`, visiting `/dashboard` while signed-out should redirect to `/sign-in`. Without keys: type-check passes; runtime will warn but build succeeds.

- [ ] **Step 6: Commit**

```bash
git add apps/web/middleware.ts apps/web/src/app/sign-in apps/web/src/app/sign-up apps/web/src/app/\(app\)
git commit -m "feat(web): Clerk middleware, sign-in/sign-up, dashboard skeleton"
```

---

## Task 19: Typed API client (web → api)

**Files:**
- Create: `apps/web/src/lib/api-client.ts`

- [ ] **Step 1: Implement `api-client.ts`**

```ts
// apps/web/src/lib/api-client.ts
"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(public code: string, message: string, public detail: unknown, public status: number) {
    super(message);
  }
}

type ApiEnvelope<T> = T | { error: { code: string; message: string; detail: unknown } };

async function parseEnvelope<T>(resp: Response): Promise<T> {
  const body = (await resp.json()) as ApiEnvelope<T>;
  if (!resp.ok || (typeof body === "object" && body !== null && "error" in body)) {
    const err = (body as { error: { code: string; message: string; detail: unknown } }).error;
    throw new ApiError(err?.code ?? "unknown", err?.message ?? resp.statusText, err?.detail, resp.status);
  }
  return body as T;
}

export function useApi() {
  const { getToken } = useAuth();

  const request = useCallback(
    async <T>(path: string, init: RequestInit = {}): Promise<T> => {
      const token = await getToken();
      const headers = new Headers(init.headers);
      headers.set("content-type", "application/json");
      if (token) headers.set("authorization", `Bearer ${token}`);
      const resp = await fetch(`${BASE}${path}`, { ...init, headers });
      return parseEnvelope<T>(resp);
    },
    [getToken],
  );

  return { request };
}

// Typed shapes — these are hand-written for P1; later sub-projects move to OpenAPI codegen.
export interface MeResponse {
  id: string;
  email: string;
  credit_balance: number;
}
```

- [ ] **Step 2: Type-check**

From `apps/web/`: `pnpm typecheck`
Expected: success.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/lib/api-client.ts
git commit -m "feat(web): typed api client with Clerk-token auth"
```

---

## Task 20: `shared-types` placeholder package

**Files:**
- Create: `packages/shared-types/package.json`
- Create: `packages/shared-types/tsconfig.json`
- Create: `packages/shared-types/src/index.ts`

- [ ] **Step 1: Create `packages/shared-types/package.json`**

```json
{
  "name": "@faceless-yt/shared-types",
  "version": "0.0.0",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "scripts": {
    "build": "echo \"types-only package\"",
    "lint": "echo \"no lint\""
  }
}
```

- [ ] **Step 2: Create `packages/shared-types/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "esnext",
    "moduleResolution": "bundler",
    "strict": true,
    "declaration": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*.ts"]
}
```

- [ ] **Step 3: Create `packages/shared-types/src/index.ts`**

```ts
// Hand-written stubs in P1. Replaced by OpenAPI-generated types in a later sub-project.
export interface MeResponseDTO {
  id: string;
  email: string;
  credit_balance: number;
}
```

- [ ] **Step 4: Install + verify workspace recognizes the package**

From repo root: `pnpm install`
Run: `pnpm -r exec node -e "console.log('ok')"`
Expected: includes the `@faceless-yt/shared-types` package in output.

- [ ] **Step 5: Commit**

```bash
git add packages/shared-types
git commit -m "feat(shared-types): placeholder package for cross-app types"
```

---

## Task 21: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [master, main]
  pull_request:

jobs:
  api:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: faceless
          POSTGRES_PASSWORD: faceless
          POSTGRES_DB: faceless
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U faceless"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql+asyncpg://faceless:faceless@localhost:5432/faceless
      REDIS_URL: redis://localhost:6379/0
      S3_BUCKET: ci-bucket
      S3_ENDPOINT: http://localhost:9000
      S3_ACCESS_KEY: ak
      S3_SECRET_KEY: sk
      CLERK_JWT_ISSUER: https://test.clerk.accounts.dev
      CLERK_JWT_AUDIENCE: https://app.test
      ENCRYPTION_KEY: AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
    defaults:
      run:
        working-directory: apps/api
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      - name: Lint
        run: ruff check .
      - name: Test
        run: pytest

  web:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/web
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "pnpm"
          cache-dependency-path: pnpm-lock.yaml
      - name: Install
        run: pnpm install --frozen-lockfile
        working-directory: .
      - name: Typecheck
        run: pnpm typecheck
      - name: Lint
        run: pnpm lint
      - name: Build
        env:
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: pk_test_dummy_for_build
          CLERK_SECRET_KEY: sk_test_dummy_for_build
        run: pnpm build
```

- [ ] **Step 2: Push branch + verify CI**

```bash
git checkout -b ci/initial
git add .github/workflows/ci.yml
git commit -m "ci: GitHub Actions for api lint/test and web typecheck/lint/build"
git push -u origin ci/initial
```
Open the PR. Expected: both `api` and `web` jobs go green.

- [ ] **Step 3: Merge to default branch once green**

(Per repo policy — squash or merge.)

---

## Task 22: P1 closeout — README updates + verification checklist

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update `README.md`**

```markdown
# Faceless YT

Multi-tenant SaaS for AI-generated faceless YouTube channel automation.

## Tech stack

- **Backend** (`apps/api`): Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, arq, Clerk JWT auth.
- **Frontend** (`apps/web`): Next.js 15 (App Router), TypeScript, Tailwind, Clerk.
- **Infra**: Postgres 16, Redis 7, MinIO (R2 stand-in for local dev).
- **Deploy target**: Railway (api, worker, web services + managed Postgres + Redis; storage on Cloudflare R2).

## Local development

Prereqs: Docker Desktop, Node 20+, pnpm 9, Python 3.12.

```bash
# 1) Bring up infra
docker compose up -d

# 2) Set up backend
cd apps/api
python -m venv .venv && . .venv/Scripts/activate    # or: source .venv/bin/activate (Unix)
pip install -e ".[dev]"
cp .env.example .env                                 # then edit ENCRYPTION_KEY etc.
alembic upgrade head

# 3) Run backend
uvicorn faceless.main:app --reload --port 8000
# (separate terminal) arq faceless.worker.WorkerSettings

# 4) Frontend
cd ../../
pnpm install
cd apps/web
cp .env.example .env.local                           # then add real Clerk dev keys
pnpm dev
```

Visit:
- http://localhost:3000 — marketing
- http://localhost:3000/dashboard — protected (requires sign-in)
- http://localhost:8000/api/docs — OpenAPI / Swagger

## Tests

```bash
cd apps/api && pytest        # backend (unit + integration)
cd apps/web && pnpm typecheck && pnpm lint && pnpm build   # frontend
```

## Documentation

- `docs/superpowers/specs/` — design specs
- `docs/superpowers/plans/` — implementation plans, one per sub-project (P1, P2, …)
```

- [ ] **Step 2: Run the full verification checklist**

Confirm each of these works in a fresh checkout:

- [ ] `docker compose up -d` brings up postgres, redis, minio (all healthy)
- [ ] `pnpm install` (root) installs all workspaces
- [ ] `cd apps/api && pip install -e ".[dev]" && alembic upgrade head` succeeds
- [ ] `cd apps/api && pytest` — all tests pass
- [ ] `cd apps/api && uvicorn faceless.main:app --port 8000` — `/api/v1/health` returns `{"status":"ok",...}`
- [ ] `cd apps/api && arq faceless.worker.WorkerSettings` — worker starts, idles
- [ ] `cd apps/web && pnpm typecheck` — passes
- [ ] `cd apps/web && pnpm lint` — passes
- [ ] `cd apps/web && pnpm build` (with dummy Clerk keys) — succeeds
- [ ] `cd apps/web && pnpm dev` — `http://localhost:3000` renders marketing page
- [ ] CI on push — both `api` and `web` jobs green

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: P1 closeout — README with full local-dev setup"
```

---

## What's NOT in P1 (and where it lands)

| Concern | Sub-project |
|---|---|
| Stripe Checkout, credit ledger atomicity, refund flow | P2 — Credits & Billing |
| OpenAI / Kling / ElevenLabs / Whisper provider adapters; FFmpeg compose; state machine; arq stage handlers | P3 — Generation Pipeline |
| YouTube OAuth, Data API upload, approval queue API + WebSocket | P4 — YouTube Publishing & Approval Queue |
| Series CRUD, cron-based auto-generation, analytics polling, learning loop | P5 — Series, Scheduling & Learning Loop |
| Full UI: channels, series editor, queue, job detail with live progress, billing, published analytics | P6 — Frontend |
| Sentry, Prometheus + Grafana, Railway deployment manifests, smoke cron | P7 — Observability & Deployment |

---

## Self-Review Notes

**Spec coverage of P1 deliverables (spec § / P1 task):**
- §1 boundaries (Clerk, Storage, Postgres, Redis) → Tasks 2, 11
- §2 all data-model tables → Task 9 (baseline migration)
- §2 User ORM model + indices → Task 8
- §6 API conventions (error envelope, JSON) → Task 12
- §6 `/me` endpoint → Task 15
- §6 health endpoint → Task 14
- §7 repo layout → Tasks 1–3, 17, 20
- §7 Configuration (pydantic-settings + env vars) → Task 4
- §7 Local dev (docker-compose + Make) → Tasks 1, 2
- §9 logging → Task 5
- §9 security (encryption util for OAuth tokens) → Task 6
- arq worker entry → Task 16
- CI → Task 21

**Out-of-spec-for-P1 items deferred:**
- Pipeline state machine, providers, FFmpeg, Stripe, YouTube OAuth, scheduling, learning loop, full UI, observability beyond logs — all assigned to P2–P7.

**Type-consistency check:** `MeResponse` (api/routes/me.py) and `MeResponseDTO`/`MeResponse` (web/lib/api-client.ts, packages/shared-types) all use the same field names: `id`, `email`, `credit_balance`. ✓

**Placeholder scan:** No "TBD"/"TODO"/"implement later" markers in any task code. Env-var placeholders in `.env.example` (`PLACEHOLDER_REPLACE_ME`, `pk_test_REPLACE_ME`) are deliberate and documented. ✓
