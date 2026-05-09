# AI Copilot Optimizer — GitHub Copilot Instructions

## Essential Context Files — Read These First

Before implementing any feature, read the relevant files:

- `.github/AI_CONTEXT.md` — full project context, runtime stack, env vars, key design decisions, gotchas
- `.github/architecture.md` — component diagram, all request flows, service responsibilities
- `.github/database-rules.md` — DB schema, SQLAlchemy conventions, naming rules, migration process
- `specs/` — detailed spec for each endpoint and UI component

## Project Purpose
A local AI coding assistant layer that reduces token usage and improves code understanding
for Java monoliths (Servlets, JSP, Spring Boot, Spring Batch). All AI/ML logic lives in a
Python FastAPI backend. Editor plugins (VS Code, IntelliJ) query the backend. A Vite+React
dashboard provides observability.

## Architecture
```
Editor (VS Code / IntelliJ)
  │  sends: JWT + query + git diff + symbols
  ▼
FastAPI Backend (Python 3.12)
  ├── Sanitizer   → strips secrets before any processing
  ├── Redis       → hot cache (SHA256 hash key, 24h TTL)
  ├── FAISS       → vector similarity search (cosine ≥ 0.9)
  ├── Postgres    → persistent storage (SQLAlchemy async)
  └── OpenAI      → fallback (gpt-4.1-mini, max_tokens=300)
  ▼
Vite + React Dashboard
  └── pages: Dashboard, CacheViewer, Metrics (Recharts)
```

## Tech Stack
| Layer          | Technology                          |
|----------------|-------------------------------------|
| Backend        | Python 3.12, FastAPI, Uvicorn       |
| Vector search  | FAISS (faiss-cpu), SentenceTransformers all-MiniLM-L6-v2 |
| Hot cache      | Redis (redis-py async)              |
| Persistence    | Postgres + SQLAlchemy 2.x async     |
| LLM fallback   | OpenAI SDK (gpt-4.1-mini)           |
| Auth           | JWT (python-jose), HS256            |
| Dashboard      | Vite + React 18 + TypeScript        |
| Charts         | Recharts                            |
| VS Code ext    | TypeScript, vscode API              |
| IntelliJ plugin| Kotlin, IntelliJ Platform Plugin SDK|

## Monorepo Layout
```
ai-copilot-optimizer/
├── .github/
│   ├── copilot-instructions.md   ← YOU ARE HERE
│   └── workflows/ci.yml
├── specs/                        ← SDD spec files (read before implementing)
├── backend/                      ← Python FastAPI
├── dashboard/                    ← Vite + React + TypeScript
├── vscode-extension/             ← TypeScript VS Code extension
├── intellij-plugin/              ← Kotlin IntelliJ plugin
├── scripts/                      ← git hooks installer
└── docker-compose.yml
```

## Coding Conventions

### Python (backend/)
- Python 3.12, async/await everywhere
- Pydantic v2 for all request/response models
- SQLAlchemy 2.x async sessions (`AsyncSession`)
- Type hints on all function signatures
- `os.environ.get(...)` for secrets — never hardcoded
- Routers in `backend/routers/`, services in `backend/services/`
- Every file starts with `# See: specs/<path>` comment

### TypeScript (dashboard/, vscode-extension/)
- React 18 functional components + hooks only (no class components)
- Strict TypeScript (`"strict": true` in tsconfig)
- Axios for HTTP with interceptors for JWT + 401 handling
- JWT stored in `localStorage` (dashboard) or VS Code `SecretStorage` (extension)

### Kotlin (intellij-plugin/)
- IntelliJ Platform Plugin SDK, Kotlin 1.9+
- PSI for symbol extraction, no reflection
- OkHttp for HTTP calls to backend
- JWT stored in IntelliJ `PasswordSafe`

## Security Rules (ALWAYS enforce)
1. NEVER hardcode secrets, passwords, API keys, or JWT secrets
2. ALWAYS run `sanitizer.sanitize()` before embedding or storing any user input
3. ALWAYS validate JWT on every protected endpoint
4. NEVER log raw user queries (log query hash only)
5. Limit git diff to 4000 chars, symbols to 50, dependencies to 30

## Performance Constraints
- Max diff size: 4000 characters (truncate silently)
- Max symbols extracted: 50
- Max dependency graph nodes: 30
- Parallel processing: use `asyncio.gather` for independent I/O
- FAISS index persisted to `./data/faiss.index` and loaded at startup

## How to Read Spec Files
Each file in `specs/` follows this template:
1. **Purpose** — why this component exists
2. **Inputs** — fields, types, required/optional
3. **Outputs** — response shape
4. **Behavior / Logic** — numbered rules, IF/ELSE conditions
5. **Acceptance Criteria** — checkboxes for verification
6. **Edge Cases** — how to handle them
7. **Dependencies** — other specs or services referenced

Always read the relevant spec file before implementing a component.
