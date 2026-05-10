# See: specs/OVERVIEW.md
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models.db import engine, Base
from .routers import auth, query, upsert, stats, review
from .services.faiss_service import faiss_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Startup: creating database tables")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Startup: loading FAISS index from disk")
    faiss_service.load()

    yield

    # --- Shutdown ---
    logger.info("Shutdown: persisting FAISS index to disk")
    faiss_service.save()
    await engine.dispose()


app = FastAPI(
    title="AI Copilot Optimizer",
    description="Local AI coding assistant — semantic cache for Java monolith queries",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,   prefix="/auth",   tags=["auth"])
app.include_router(query.router,  prefix="/query",  tags=["query"])
app.include_router(upsert.router, prefix="/upsert", tags=["upsert"])
app.include_router(stats.router,  prefix="/stats",  tags=["stats"])
app.include_router(review.router, prefix="/review", tags=["review"])


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
