# Spec: OVERVIEW — System Architecture

## Purpose
Central reference for all component specs. Defines data flow, component boundaries,
and shared conventions. Read this before reading any individual spec.

## Architecture Diagram
```
┌─────────────────────────────────────────────────────────────────┐
│                     EDITOR LAYER                                │
│  ┌──────────────────┐          ┌──────────────────────────┐    │
│  │  VS Code Ext     │          │  IntelliJ Plugin          │   │
│  │  (TypeScript)    │          │  (Kotlin)                 │   │
│  │  ─ onSave *.java │          │  ─ Tools → Build Prompt   │   │
│  │  ─ git diff      │          │  ─ PSI symbol extract     │   │
│  │  ─ LSP symbols   │          │  ─ BFS dep graph          │   │
│  └────────┬─────────┘          └────────────┬─────────────┘   │
└───────────┼────────────────────────────────┼────────────────────┘
            │ JWT + query + diff + symbols    │
            ▼                                ▼
┌───────────────────────────────────────────────────────────────┐
│                   FASTAPI BACKEND (Python 3.12)               │
│                                                               │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐  ┌──────────┐  │
│  │ /query   │   │ /upsert  │   │ /stats   │  │ /review  │  │
│  └────┬─────┘   └────┬─────┘   └──────────┘  └────┬─────┘  │
│       │              │                              │         │
│  ┌────▼──────────────▼──────────────────────────────▼──────┐ │
│  │                  Sanitizer (strips secrets)              │ │
│  └────┬───────────────────────────────────────────────┬────┘ │
│       │                                               │       │
│  ┌────▼──────┐  ┌────────────┐  ┌────────────┐  ┌────▼────┐ │
│  │  Redis    │  │   FAISS    │  │  Postgres  │  │ OpenAI  │ │
│  │ hot cache │  │ vec search │  │ persistent │  │fallback │ │
│  │ 24h TTL   │  │cosine≥0.9  │  │ SQLAlchemy │  │gpt-4.1  │ │
│  └───────────┘  └────────────┘  └────────────┘  └─────────┘ │
└───────────────────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────┐
│              VITE + REACT DASHBOARD (TypeScript)              │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Dashboard  │  │ Cache Viewer │  │ Metrics (Recharts)   │  │
│  │ stat cards │  │ Q/A table    │  │ line + bar charts    │  │
│  └────────────┘  └──────────────┘  └──────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

## Query Flow (Happy Path)
```
1. Editor sends POST /query {query, context, prompt_type, JWT}
2. Backend extracts user_id + team_id from JWT
3. Sanitizer strips secrets from query
4. Compute SHA256(sanitized_query) → query_hash
5. CHECK Redis: GET query_hash
   → HIT:  log request (cache_hit=true), return cached response
6. Embed query with SentenceTransformers all-MiniLM-L6-v2
7. SEARCH FAISS (cosine similarity, top-1)
   → similarity >= 0.9: log request (cache_hit=true), update Redis, return response
8. CALL OpenAI gpt-4.1-mini (max_tokens=300)
9. STORE: upsert to FAISS, insert to Postgres, set Redis (TTL=24h)
10. LOG request (cache_hit=false, tokens_used=N)
11. Return response
```

## Component Responsibility Matrix
| Component         | Owns                           | Does NOT own                  |
|-------------------|--------------------------------|-------------------------------|
| Sanitizer         | Secret stripping               | Embedding, storage            |
| Redis service     | Hot cache read/write           | Persistence, embeddings       |
| FAISS service     | Vector index + similarity      | Metadata, user isolation      |
| Postgres models   | Metadata, logs, history        | Vectors                       |
| OpenAI service    | LLM calls                      | Caching, storage              |
| JWT auth          | Token validation, user context | Password storage              |

## Shared Secrets / Env Vars
| Variable        | Used by          | Description                     |
|-----------------|------------------|---------------------------------|
| JWT_SECRET      | backend/auth     | HS256 signing key (min 32 chars)|
| DATABASE_URL    | backend/models   | Async Postgres URL              |
| REDIS_URL       | backend/services | Redis connection URL            |
| OPENAI_API_KEY  | backend/services | OpenAI API key                  |

## Spec File Index
| File                                      | Describes              |
|-------------------------------------------|------------------------|
| specs/backend/query-endpoint.md           | POST /query            |
| specs/backend/upsert-endpoint.md          | POST /upsert           |
| specs/backend/stats-endpoint.md           | GET /stats             |
| specs/backend/review-endpoint.md          | POST /review           |
| specs/dashboard/dashboard-page.md         | Dashboard page         |
| specs/dashboard/cache-viewer-page.md      | Cache Viewer page      |
| specs/dashboard/metrics-page.md           | Metrics page           |
| specs/vscode-extension/build-prompt-command.md | VS Code command   |
| specs/vscode-extension/webview-panel.md   | WebView panel          |
| specs/intellij-plugin/build-prompt-action.md | IntelliJ action     |
| specs/intellij-plugin/tool-window.md      | IntelliJ tool window   |
| specs/git-hooks/pre-push-review.md        | pre-push git hook      |
