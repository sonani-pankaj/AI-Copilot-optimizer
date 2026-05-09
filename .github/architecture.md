# Architecture — AI Copilot Optimizer

---

## High-Level Component Diagram

```
┌─────────────────────────┐   ┌──────────────────────────┐
│   VS Code Extension     │   │   IntelliJ Plugin         │
│   TypeScript            │   │   Kotlin                  │
│                         │   │                           │
│  promptBuilder.ts       │   │  PsiSymbolExtractor.kt    │
│  backendClient.ts       │   │  BackendClient.kt         │
│  webviewPanel.ts        │   │  AiPromptToolWindow.kt    │
└──────────┬──────────────┘   └──────────┬────────────────┘
           │  POST /query  JWT + payload  │
           └──────────────┬──────────────┘
                          ▼
           ┌──────────────────────────────┐
           │     FastAPI Backend          │  :8000
           │     Python 3.12 + Uvicorn    │
           │                              │
           │  routers/                    │
           │    auth.py    POST /auth/login│
           │    query.py   POST /query    │
           │    upsert.py  POST /upsert   │
           │    stats.py   GET  /stats    │
           │    review.py  POST /review   │
           │                              │
           │  services/                   │
           │    sanitizer.py   ← always first
           │    redis_service.py          │
           │    faiss_service.py          │
           │    openai_service.py         │
           │                              │
           │  auth/jwt.py  HS256 verify   │
           └──┬──────┬──────────┬─────────┘
              │      │          │
     ┌────────▼──┐ ┌─▼───────┐ ┌▼──────────────────────┐
     │  Redis 7  │ │ FAISS   │ │  Postgres 16           │
     │  :6379    │ │in-process│ │  :5432                 │
     │  hot cache│ │cosine   │ │  cache_entries         │
     │  24h TTL  │ │similarity│ │  request_logs          │
     └───────────┘ └────┬────┘ └────────────────────────┘
                        │ persist
                  ┌─────▼──────────────────┐
                  │  ./data/faiss.index    │
                  │  ./data/faiss.index    │
                  │        .meta.npy       │
                  └────────────────────────┘
                          │ LLM fallback
                  ┌───────▼───────────────────────────────┐
                  │  Ollama  (local)  :11434               │
                  │  OR OpenAI cloud  api.openai.com       │
                  │  via OpenAI SDK with base_url override │
                  │  model: gemma3:latest (default)        │
                  └───────────────────────────────────────┘

           ┌──────────────────────────────┐
           │   Vite + React Dashboard     │  :5173
           │   pages: Dashboard           │
           │          CacheViewer         │
           │          Metrics (Recharts)  │
           │          Login               │
           │   api/client.ts (Axios)      │
           └──────────────────────────────┘
```

---

## Request Flow — POST /query (cache-first)

```
Client sends:  { query, prompt_type, language, context? }

Step 1  sanitizer.sanitize(query)
        → strips passwords, API keys, JWTs, AWS keys, PEM blocks, connection strings
        → if result is empty → 422

Step 2  query_hash = SHA-256(sanitized_query)
        Redis GET(query_hash)
        → HIT  → return { response, cache_hit: true, tokens_used: 0 }
                 [background] log to RequestLog

Step 3  FAISS search(sanitized_query)
        → embed via all-MiniLM-L6-v2 (384-dim, L2-normalized → cosine via IndexFlatIP)
        → find nearest vector
        → similarity ≥ 0.9?
           YES → fetch CacheEntry from Postgres by FAISS id_map UUID
                 Redis SET(query_hash, response)   ← warm the Redis cache
                 return { response, cache_hit: true, similarity }
                 [background] log to RequestLog
           NO  → continue

Step 4  Build prompt:
        if req.context present:
            prompt = "Context:\n{sanitized context}\n\nQuestion:\n{sanitized_query}"
        else:
            prompt = sanitized_query

        LLM call: openai_service.complete(prompt, prompt_type)
        → system prompt varies by prompt_type (QUERY / GENERATE_TESTS / REVIEW)
        → REVIEW uses json_object response_format
        → raises RuntimeError on failure → 502

Step 5  [background tasks, non-blocking]:
        - INSERT CacheEntry (query_hash, query, response, tokens_saved, model_used)
        - FAISS add vector with CacheEntry UUID as id
        - Redis SET(query_hash, response, TTL=24h)
        - INSERT RequestLog (user_id, team_id, query_hash, cache_hit=False, tokens_used)

Step 6  return { response, cache_hit: false, tokens_used, prompt_type }
```

---

## Request Flow — POST /review

```
Client sends:  { diff, pr_title?, pr_description? }

Step 1  diff truncated to 4000 chars (enforced by Pydantic schema max_length)
Step 2  LLM called with REVIEW system prompt → expects JSON output
Step 3  Response parsed → ReviewResponse { bugs[], performance[], security[], summary }
Step 4  NOT cached (reviews are diff-specific, not reusable)
Step 5  return ReviewResponse
```

---

## Request Flow — POST /upsert

```
Client sends:  { query, response, tokens_saved, model_used }

Step 1  sanitize(query)
Step 2  query_hash = SHA-256(sanitized_query)
Step 3  Check if CacheEntry exists for query_hash (upsert semantics)
        → EXISTS: return existing id, skip insert
        → NEW: INSERT CacheEntry
Step 4  FAISS add vector for new entry
Step 5  Redis SET(query_hash, response)
Step 6  return { id, query_hash, message }
```

---

## VS Code Extension Data Flow

```
Java file saved  OR  Command Palette  OR  Right-click folder
        │
        ▼
promptBuilder.ts
  buildPrompt(editor)            ← single file
  buildPromptFromFolder(uri)     ← folder, finds all **/*.java
        │
        │  extract via vscode.commands.executeCommand('vscode.executeDocumentSymbolProvider')
        │  extract git diff via child_process.execSync('git diff HEAD')
        │  truncate diff to 4000 chars, symbols to 50 total
        │
        ▼  PromptPayload { query, prompt_type, language }
backendClient.ts
  queryBackend(payload, jwt)
        │  POST http://localhost:8000/query
        │  Authorization: Bearer <jwt from SecretStorage>
        │  on 401: delete stored jwt, show error
        ▼
webviewPanel.ts
  AiPromptPanel.getOrCreate(context)
  panel.setState({ loading | response | error | cacheHit | similarity })
        │
        ▼
  WebView HTML rendered in VS Code sidebar panel
```

---

## Services — Responsibilities

### `sanitizer.py`
- Called before ANY embedding, storage, or LLM call
- Regex patterns: passwords, API keys, secrets/tokens, AWS keys, JWTs, PEM blocks,
  JDBC/MongoDB/Postgres connection strings, Authorization headers
- Never raises — silently returns original on error

### `redis_service.py`
- Key: SHA-256 hex of sanitized query (64 chars)
- TTL: 24 hours
- All operations wrapped in try/except — Redis failure is non-fatal (degrades to FAISS)
- Uses `redis.asyncio` (async client)

### `faiss_service.py`
- Model: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- Index type: `IndexFlatIP` (inner product on L2-normalized vectors = cosine similarity)
- Thread-safe via `asyncio.Lock`
- ID map: `dict[int, str]` mapping FAISS integer ID → Postgres UUID string
- Persisted to disk on shutdown, loaded on startup
- Similarity threshold: 0.9 (defined in `query.py`, not the service)

### `openai_service.py`
- Single `AsyncOpenAI` client, lazily initialized
- `OPENAI_BASE_URL` env var → routes to Ollama when set to `http://localhost:11434/v1`
- `LLM_MODEL` env var → model name, defaults to `gpt-4.1-mini`
- System prompts per `PromptType`: QUERY | GENERATE_TESTS | REVIEW
- REVIEW uses `response_format: { type: json_object }`
- Raises `RuntimeError` on any API error → caller returns 502

### `auth/jwt.py`
- HS256, 24h expiry
- `JWT_SECRET` read at module import time — must be set before `uvicorn` starts
- `verify_token` is a FastAPI `Depends` used on every protected router

---

## Dashboard Architecture

```
Vite + React 18 SPA
  App.tsx
    BrowserRouter
      /login    → Login.tsx    → POST /auth/login → localStorage.jwt
      /*        → RequireAuth (checks localStorage.jwt)
        /        → Dashboard.tsx  → GET /stats (30s polling)
        /cache   → CacheViewer.tsx → GET /upsert (paginated), filter by user_id
        /metrics → Metrics.tsx   → GET /stats/history?days=N (7/14/30)

api/client.ts
  axios instance
    baseURL = VITE_API_URL ?? '' (Vite proxy in dev → localhost:8000)
    request interceptor: inject Authorization: Bearer {localStorage.jwt}
    response interceptor: 401 → clear jwt, redirect /login
```

---

## IntelliJ Plugin Architecture

```
BuildAiPromptAction.kt    ← AnAction, triggered by Ctrl+Alt+A or right-click
  │
  ├── PsiSymbolExtractor.kt   ← PSI tree walk, extracts class/method/field names
  ├── GitDiffUtil.kt          ← git diff via ProcessBuilder
  ├── DependencyGraphWalker.kt ← walks import graph (max 30 nodes)
  └── BackendClient.kt        ← OkHttp POST to backend /query
        │  JWT from PasswordSafe (AiOptimizerSettings.kt)
        ▼
AiPromptToolWindow.kt     ← Tool window panel shows response
AiOptimizerSettings.kt    ← Settings UI: backend URL + JWT token
```

---

## Docker Compose Services

| Service | Image | Port | Data |
|---------|-------|------|------|
| postgres | postgres:16-alpine | 5432:5432 | named volume `postgres_data` |
| redis | redis:7-alpine | 6379:6379 | in-memory, maxmemory 256mb, allkeys-lru |
| backend | ./backend/Dockerfile | 8000:8000 | mounts `.env` |
| dashboard | ./dashboard/Dockerfile | 5173:80 | nginx serves built SPA |

For local development, only `postgres` and `redis` services are needed from Docker.
Run backend and dashboard natively for hot-reload.

---

## Adding a New Feature — Checklist

1. Read the relevant spec in `specs/` first (or create one)
2. Backend: add router in `backend/routers/`, register in `main.py`, add Pydantic schemas in `models/schemas.py`
3. Always call `sanitizer.sanitize()` on user input before processing
4. Always validate JWT via `Depends(verify_token)` on new protected endpoints
5. Use background tasks for non-critical writes (DB, cache)
6. Dashboard: add API helper to `api/client.ts`, new page in `pages/`, route in `App.tsx`
7. VS Code extension: compile (`npm run compile`) and repackage (`.vsix`) after any change
8. Update `.github/AI_CONTEXT.md` if the architecture changes
