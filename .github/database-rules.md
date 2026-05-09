# Database Rules — AI Copilot Optimizer

All database access goes through SQLAlchemy 2.x async (`AsyncSession`).
Tables are created automatically on backend startup via `Base.metadata.create_all`.
No manual migrations required for schema changes during development — drop and recreate.
For production schema changes, use Alembic (already in `requirements.txt`).

---

## Engine Configuration

```python
# backend/models/db.py
engine = create_async_engine(
    DATABASE_URL,   # postgresql+asyncpg://...
    echo=False,     # set True temporarily for SQL debug logging
    pool_pre_ping=True,   # test connections before using from pool
)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
```

**Connection string format**: `postgresql+asyncpg://user:password@host:port/dbname`

---

## Tables

### `cache_entries`

Stores every unique query/response pair. One row per unique sanitized query.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default `uuid4` | Postgres native UUID |
| `user_id` | VARCHAR(255) | NOT NULL, indexed | JWT `sub` claim |
| `team_id` | VARCHAR(255) | nullable, indexed | JWT `team_id` claim; NULL = personal |
| `query_hash` | VARCHAR(64) | NOT NULL, UNIQUE, indexed | SHA-256 hex of sanitized query |
| `query` | TEXT | NOT NULL | Full sanitized query text |
| `response` | TEXT | NOT NULL | LLM response text |
| `tokens_saved` | INTEGER | default 0 | Tokens this entry has saved on cache hits |
| `model_used` | VARCHAR(100) | default `'gpt-4.1-mini'` | Actual model that generated the response |
| `created_at` | DATETIME | default `utcnow()`, indexed | UTC timestamp |

**Uniqueness**: `query_hash` is UNIQUE — `POST /upsert` checks for existing hash before inserting.

**FAISS link**: The UUID `id` is stored in `faiss_service._id_map[int_id] = str(uuid)`.
After a FAISS search hit, the backend does `db.get(CacheEntry, pg_id)` to fetch the response.

---

### `request_logs`

Append-only audit/analytics log. One row per API call to `POST /query`.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | UUID | PK, default `uuid4` | |
| `user_id` | VARCHAR(255) | NOT NULL, indexed | |
| `team_id` | VARCHAR(255) | nullable, indexed | |
| `query_hash` | VARCHAR(64) | NOT NULL | SHA-256 of the query (not FK to cache_entries) |
| `cache_hit` | BOOLEAN | default False | True if served from Redis or FAISS |
| `tokens_used` | INTEGER | default 0 | 0 on cache hit; actual tokens on LLM call |
| `created_at` | DATETIME | default `utcnow()`, indexed | UTC timestamp |

**Notes**:
- No foreign key to `cache_entries` — by design, to avoid write contention
- Written as a FastAPI `BackgroundTask` (non-blocking)
- Used by `/stats` and `/stats/history` endpoints for analytics

---

## Access Patterns

### `/query` endpoint
```python
# Redis check (no DB)
# FAISS search → db.get(CacheEntry, pg_id)          ← point lookup by PK
# Background: db.add(CacheEntry(...)); await db.commit()
# Background: db.add(RequestLog(...)); await db.commit()
```

### `/upsert` endpoint
```python
# Check: SELECT * FROM cache_entries WHERE query_hash = :hash LIMIT 1
# Insert if not found: db.add(CacheEntry(...))
```

### `/stats` endpoint
```python
# SELECT count(id), coalesce(sum(tokens_saved), 0) FROM cache_entries WHERE user_id = :uid
# SELECT count(id) FROM request_logs WHERE user_id = :uid
# SELECT count(id) FROM request_logs WHERE user_id = :uid AND cache_hit = true
```

### `/stats/history` endpoint
```python
# SELECT date(created_at), count(id), sum(cast(cache_hit AS int))
# FROM request_logs
# WHERE created_at >= :since AND user_id = :uid
# GROUP BY date(created_at)
# ORDER BY date(created_at)
```
> **Note**: `func.cast(RequestLog.cache_hit, Integer)` — required because SQLAlchemy cannot
> SUM a Boolean directly in Postgres. Do NOT use `func.sum(RequestLog.cache_hit)` alone.

---

## SQLAlchemy Conventions

### Session usage
```python
# Always use the FastAPI dependency:
async def my_endpoint(db: AsyncSession = Depends(get_db)):
    ...

# Never instantiate AsyncSessionLocal directly in a router.
# In background tasks that receive a db session, the session is passed as a parameter.
```

### Querying
```python
# SELECT with filter:
stmt = select(CacheEntry).where(CacheEntry.query_hash == hash_val)
result = await db.execute(stmt)
entry = result.scalar_one_or_none()

# Point lookup by PK:
entry = await db.get(CacheEntry, uuid_value)

# Aggregates:
stmt = select(func.count(CacheEntry.id))
count = (await db.execute(stmt)).scalar_one()

# SUM of Boolean column (must cast):
stmt = select(func.sum(func.cast(RequestLog.cache_hit, Integer)))
```

### Writing
```python
# Insert:
obj = CacheEntry(user_id=..., query_hash=..., ...)
db.add(obj)
await db.commit()
await db.refresh(obj)   # only needed if you need server-generated values back

# Update:
obj.tokens_saved += delta
await db.commit()
```

---

## Naming Conventions

| Thing | Convention | Example |
|-------|-----------|---------|
| Table names | snake_case plural | `cache_entries`, `request_logs` |
| Column names | snake_case | `user_id`, `created_at`, `query_hash` |
| Primary key | always `id`, UUID type | `id = Column(UUID(as_uuid=True), ...)` |
| Timestamps | always UTC, column name `created_at` | `default=datetime.utcnow` |
| Foreign keys | not used (by design — avoids join complexity) | — |
| Indexes | on all filter/sort columns | `index=True` in Column definition |
| Enum-like values | stored as VARCHAR, validated by Pydantic | `model_used`, `severity` |

---

## Scoping Rules (multi-tenant)

Every query is scoped to either a **user** or a **team**:

```python
if scope_team:
    stmt = stmt.where(Model.team_id == scope_team)
else:
    stmt = stmt.where(Model.user_id == scope_user)
```

- `team_id` comes from the JWT payload (`token.team_id`)
- If `team_id` is present, the team scope takes precedence
- A query parameter `?team_id=` on `/stats` can override the JWT team_id
- This pattern must be applied consistently to all new queries on these tables

---

## Migration Rules

**Development** (no data to preserve):
```bash
# Drop and recreate all tables:
# Just restart the backend — Base.metadata.create_all runs on startup
# Or to force a fresh DB:
docker compose down -v   # removes postgres_data volume
docker compose up -d postgres
# Restart backend
```

**Production / Alembic**:
```bash
cd backend
alembic revision --autogenerate -m "describe change"
# Review the generated migration in alembic/versions/
alembic upgrade head
```

Rules for writing migrations:
- Never drop columns — add new nullable columns with defaults
- Never rename columns — add new, backfill, deprecate old
- All new columns must have `server_default` or `nullable=True`
- Test migration on a copy of the DB before applying to production

---

## Adding a New Table — Checklist

1. Add model class to `backend/models/db.py`, inherit from `Base`
2. Add UUID primary key (`default=uuid.uuid4`)
3. Add `created_at` column with `default=datetime.utcnow, index=True`
4. Add indexes on all columns used in WHERE clauses
5. Add Pydantic schemas to `backend/models/schemas.py`
6. Add `user_id` + `team_id` columns if the table is user-scoped
7. Apply team/user scoping pattern in any queries on the table
8. Update this file with the table definition
