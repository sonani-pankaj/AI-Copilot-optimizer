# AI Copilot Optimizer

A local AI coding assistant layer that reduces token usage and improves code understanding
for Java monoliths (Servlets, JSP, Spring Boot, Spring Batch).

```
Editor (VS Code / IntelliJ)
  │  sends: JWT + query + git diff + symbols
  ▼
FastAPI Backend (Python 3.12)
  ├── Sanitizer   → strips secrets before any processing
  ├── Redis       → hot cache (SHA-256 hash key, 24h TTL)
  ├── FAISS       → vector similarity search (cosine ≥ 0.9)
  ├── Postgres    → persistent storage (SQLAlchemy async)
  └── OpenAI      → fallback (gpt-4.1-mini, max_tokens=300)
  ▼
Vite + React Dashboard
  └── pages: Dashboard, CacheViewer, Metrics (Recharts)
```

## Prerequisites

- Docker & Docker Compose v2
- Node 20+ (for dashboard development)
- Python 3.12+ (for backend development)

## Quick Start

### 1. Configure environment variables

```bash
cp .env.example .env
# Edit .env and set:
#   JWT_SECRET=<random 32+ char string>
#   OPENAI_API_KEY=sk-...
#   DEMO_PASSWORD_HASH=<bcrypt hash of your password>
```

Generate a bcrypt hash for your password:
```bash
python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('yourpassword'))"
```

### 2. Start all services

```bash
docker compose up -d
```

- Dashboard: http://localhost:5173
- Backend API docs: http://localhost:8000/docs

### 3. Install the VS Code extension

```bash
cd vscode-extension
npm install
npm run compile
# Then press F5 in VS Code to launch the Extension Development Host
```

Set your JWT token via the command palette: `AI Copilot Optimizer: Set Backend JWT Token`

### 4. Install git hooks

```bash
bash scripts/install-hooks.sh
export AI_OPTIMIZER_JWT="<your JWT token>"
```

## Development

### Backend

```bash
cd backend
pip install -r requirements.txt
JWT_SECRET=dev-secret \
  DATABASE_URL=postgresql+asyncpg://postgres:changeme@localhost:5432/ai_optimizer \
  REDIS_URL=redis://localhost:6379/0 \
  OPENAI_API_KEY=sk-... \
  uvicorn main:app --reload
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev   # http://localhost:5173 (proxies API to :8000)
```

### IntelliJ Plugin

```bash
cd intellij-plugin
./gradlew runIde
```

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | — | Issue JWT |
| POST | `/query` | Bearer | Cache-first query |
| POST | `/upsert` | Bearer | Store cache entry |
| GET | `/upsert` | Bearer | List cache entries |
| GET | `/stats` | Bearer | Aggregate stats |
| GET | `/stats/history` | Bearer | Per-day history |
| POST | `/review` | Bearer | Git diff review |
| GET | `/health` | — | Health check |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET` | ✓ | Secret for HS256 JWT signing |
| `OPENAI_API_KEY` | ✓ | OpenAI API key |
| `DATABASE_URL` | ✓ | PostgreSQL asyncpg connection string |
| `REDIS_URL` | — | Redis URL (degraded mode if absent) |
| `DEMO_USERNAME` | — | Login username (default: `admin`) |
| `DEMO_PASSWORD_HASH` | ✓ | bcrypt hash of login password |
| `POSTGRES_PASSWORD` | — | Postgres password for docker-compose |

## Security

- All user input is sanitized (secrets stripped) before embedding or storage
- JWT tokens expire after 24 hours
- Git diffs capped at 4,000 characters, symbols at 50, dependency nodes at 30
- Tokens stored in VS Code SecretStorage / IntelliJ PasswordSafe — never in plaintext
