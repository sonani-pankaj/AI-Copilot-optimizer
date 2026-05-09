# AI_CONTEXT.md — Project Context for AI Assistants

Read this file at the start of any new chat session working on this repo.
It gives you full context so you never start cold.

---

## What This Project Is

**AI Copilot Optimizer** is a local AI coding assistant layer that reduces token usage
and improves code understanding for **Java monolith** projects (Servlets, JSP, Spring Boot,
Spring Batch). It is a full-stack monorepo with:

- A **Python FastAPI backend** that runs a 3-level cache (Redis → FAISS → LLM fallback)
- A **Vite + React dashboard** for observability
- A **VS Code extension** (TypeScript) that sends Java file/folder context to the backend
- An **IntelliJ plugin** (Kotlin) that does the same from inside IDEA

The whole stack runs locally. No cloud required — an Ollama model replaces OpenAI.

---

## Monorepo Layout

```
ai-copilot-optimizer/
├── .github/
│   ├── copilot-instructions.md   ← high-level coding rules (read this too)
│   ├── AI_CONTEXT.md             ← YOU ARE HERE
│   ├── architecture.md           ← component diagram + data flow
│   └── database-rules.md         ← DB schema, naming conventions, migration rules
├── specs/                        ← detailed spec files — read before implementing
│   ├── OVERVIEW.md
│   ├── backend/
│   │   ├── query-endpoint.md
│   │   ├── review-endpoint.md
│   │   ├── stats-endpoint.md
│   │   └── upsert-endpoint.md
│   ├── dashboard/
│   ├── intellij-plugin/
│   └── vscode-extension/
├── backend/                      ← Python 3.12 FastAPI
├── dashboard/                    ← Vite + React 18 + TypeScript
├── vscode-extension/             ← TypeScript VS Code extension
├── intellij-plugin/              ← Kotlin IntelliJ plugin
├── scripts/                      ← git hooks
└── docker-compose.yml
```

---

## Runtime Stack (as actually deployed locally)

| Component | Technology | Port |
|-----------|-----------|------|
| Backend | Python 3.12, FastAPI, Uvicorn | 8000 |
| Dashboard | Vite + React 18 + TypeScript | 5173 |
| Database | Postgres 16 (Docker) | 5432 |
| Cache | Redis 7 (Docker) | 6379 |
| LLM | Ollama (`gemma3:latest`) | 11434 |
| Vector index | FAISS (in-process, persisted to `./data/faiss.index`) | — |

> The OpenAI SDK is used with `OPENAI_BASE_URL=http://localhost:11434/v1` and
> `OPENAI_API_KEY=ollama` to route requests to Ollama instead of OpenAI cloud.
> Switch back to real OpenAI by removing those two env vars and setting a real API key.

---

## Environment Variables (`.env` in project root)

```dotenv
# Auth
JWT_SECRET=<40-char hex>          # python -c "import secrets; print(secrets.token_hex(20))"
DEMO_USERNAME=admin
DEMO_PASSWORD_HASH=<bcrypt hash>  # python -c "import bcrypt; print(bcrypt.hashpw(b'admin', bcrypt.gensalt(12)).decode())"

# Database
DATABASE_URL=postgresql+asyncpg://postgres:changeme@localhost:5432/ai_optimizer
POSTGRES_PASSWORD=changeme

# Cache
REDIS_URL=redis://localhost:6379/0

# LLM — Ollama local (default)
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gemma3:latest

# LLM — Real OpenAI (comment out Ollama block and uncomment this)
# OPENAI_API_KEY=sk-...
# LLM_MODEL=gpt-4.1-mini
```

`backend/__init__.py` calls `load_dotenv()` as the very first statement so all
submodules see env vars at import time (critical for uvicorn `--reload` multiprocessing).

---

## How the 3-Level Cache Works (query flow)

```
VS Code Extension / IntelliJ / curl
  │  POST /query  { query, prompt_type, language }
  ▼
1. sanitizer.sanitize(query)          ← strip secrets first, always
2. SHA-256 hash → Redis GET           ← exact match, 24h TTL
   └─ HIT  → return cached response
3. FAISS cosine search (≥ 0.9)        ← semantic similarity via all-MiniLM-L6-v2
   └─ HIT  → populate Redis, return
4. LLM call (Ollama / OpenAI)         ← cold miss
   └─ store in Postgres + FAISS + Redis (background tasks)
   └─ return response
```

Cache key = SHA-256 of the sanitized query string.

---

## Key Design Decisions (don't change without reason)

| Decision | Rationale |
|----------|-----------|
| `async/await` everywhere in Python | Uvicorn is async; blocking calls would stall the event loop |
| `load_dotenv()` in `backend/__init__.py` | Uvicorn spawns subprocesses for `--reload`; only `__init__` runs in all of them |
| `bcrypt==3.2.2` pinned | passlib 1.7.4 is incompatible with bcrypt ≥ 4.0 |
| FAISS `IndexFlatIP` on L2-normalized vectors | Equivalent to cosine similarity without extra overhead |
| OpenAI SDK with `base_url` override | One code path for both Ollama and real OpenAI |
| Background tasks for DB writes | Don't block the HTTP response on Postgres writes |
| JWT stored in `SecretStorage` (VS Code) / `PasswordSafe` (IntelliJ) | Never in plaintext config |
| `sanitizer.sanitize()` before every embed/store | Prevent secrets leaking into the vector index or DB |

---

## Input Size Limits (hardcoded — do not increase without profiling)

| Field | Limit | Where enforced |
|-------|-------|----------------|
| Git diff | 4 000 chars | `promptBuilder.ts`, `ReviewRequest.diff` schema |
| Symbols per query | 50 | `promptBuilder.ts` `MAX_SYMBOLS` |
| Dependency graph nodes | 30 | spec only — not yet implemented |
| Query string | 10 000 chars | `QueryRequest.query` Pydantic field |
| Context string | 5 000 chars | `QueryRequest.context` Pydantic field |
| LLM max tokens (query) | 300 | `openai_service.py` `_MAX_TOKENS` |
| LLM max tokens (review) | 500 | `openai_service.py` review branch |

---

## Auth Flow

- Login: `POST /auth/login { username, password }` → `{ access_token }`
- Algorithm: HS256, 24h expiry
- Every protected route depends on `verify_token` (FastAPI `Depends`)
- Dashboard stores JWT in `localStorage`; extension stores in VS Code `SecretStorage`
- On 401 both clients clear the stored token and redirect/prompt for re-login

---

## VS Code Extension — Commands & Entry Points

| Command ID | Title | Trigger |
|-----------|-------|---------|
| `ai-copilot-optimizer.buildPrompt` | Build Optimized Copilot Prompt | Command Palette / auto on `.java` save |
| `ai-copilot-optimizer.buildPromptFolder` | Build Optimized Copilot Prompt (Folder) | Right-click folder in Explorer |
| `ai-copilot-optimizer.setToken` | Set Backend JWT Token | Command Palette |

Extension entry: `vscode-extension/out/extension.js` (compiled from `src/extension.ts`).
Compile: `cd vscode-extension && npm run compile`
Package: `npx @vscode/vsce package --no-dependencies` → `ai-copilot-optimizer-1.0.0.vsix`
Install: `code --install-extension ai-copilot-optimizer-1.0.0.vsix`

---

## Dashboard Pages

| Route | Component | What it shows |
|-------|-----------|---------------|
| `/` | `Dashboard.tsx` | 3 stat cards (total requests, cache hits, tokens saved), auto-refresh 30s |
| `/cache` | `CacheViewer.tsx` | Paginated table of `cache_entries`, filter by user_id, row detail modal |
| `/metrics` | `Metrics.tsx` | Recharts line (requests vs hits) + bar (tokens saved/day), 7/14/30d selector |
| `/login` | `Login.tsx` | Calls `POST /auth/login`, stores JWT in localStorage |

Axios client: `dashboard/src/api/client.ts` — JWT injected via request interceptor, 401 redirects to `/login`.

---

## Known Gotchas / Lessons Learned

1. **Run uvicorn from the project root**, not from `backend/`:
   `backend\.venv\Scripts\uvicorn.exe backend.main:app --reload --port 8000`
   Running from inside `backend/` breaks relative imports.

2. **Ollama model memory**: `llama3.2:3b` needs 15.9 GiB GPU; `gemma3:latest` needs ~4 GiB.
   Use `ollama list` to check available models before changing `LLM_MODEL`.

3. **passlib + bcrypt**: passlib 1.7.4 crashes with bcrypt ≥ 4. `bcrypt==3.2.2` is pinned in
   `requirements.txt`. Do not upgrade bcrypt.

4. **FAISS index persistence**: saved to `./data/faiss.index` + `./data/faiss.index.meta.npy`
   on shutdown, loaded on startup. The `data/` dir is git-ignored. If you delete it, the index
   rebuilds empty (responses still in Postgres, but semantic cache misses until repopulated).

5. **F5 in VS Code extension**: requires `vscode-extension/.vscode/launch.json` and `tasks.json`
   (both present in the repo). The extension folder must be the workspace root for F5 to work.

6. **Docker ports**: `docker-compose.yml` explicitly maps `5432:5432` and `6379:6379`.
   These ports are required for the backend running outside Docker to reach Postgres/Redis.

---

## Where to Read More

- Full data flow: `.github/architecture.md`
- Database schema + conventions: `.github/database-rules.md`
- Coding rules: `.github/copilot-instructions.md`
- Endpoint specs: `specs/backend/*.md`
- Extension specs: `specs/vscode-extension/*.md`
