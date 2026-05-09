# See: specs/backend/query-endpoint.md, upsert-endpoint.md, stats-endpoint.md, review-endpoint.md
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class PromptType(str, Enum):
    QUERY = "QUERY"
    GENERATE_TESTS = "GENERATE_TESTS"
    REVIEW = "REVIEW"


# ── /query ────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10_000)
    prompt_type: PromptType = PromptType.QUERY
    context: Optional[str] = Field(None, max_length=5_000)
    language: Optional[str] = "java"


class QueryResponse(BaseModel):
    response: str
    cache_hit: bool
    similarity: Optional[float] = None
    tokens_used: int = 0
    prompt_type: PromptType


# ── /upsert ───────────────────────────────────────────────────────────────────

class UpsertRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10_000)
    response: str = Field(..., min_length=1)
    tokens_saved: int = 0
    model_used: str = "gpt-4.1-mini"


class UpsertResponse(BaseModel):
    id: str
    query_hash: str
    message: str = "Stored successfully"


# ── /stats ────────────────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_entries: int
    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_ratio: float
    tokens_saved: int


class StatsHistoryPoint(BaseModel):
    date: str
    requests: int
    cache_hits: int
    tokens_saved: int


# ── /review ───────────────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    diff: str = Field(..., max_length=4_000)
    pr_title: Optional[str] = Field(None, max_length=200)
    pr_description: Optional[str] = Field(None, max_length=1_000)


class ReviewIssue(BaseModel):
    severity: str        # HIGH | MEDIUM | LOW
    category: str        # bug | performance | security
    description: str
    line_hint: Optional[str] = None


class ReviewResponse(BaseModel):
    bugs: List[ReviewIssue] = []
    performance: List[ReviewIssue] = []
    security: List[ReviewIssue] = []
    summary: str


# ── /cache list ───────────────────────────────────────────────────────────────

class CacheEntryDTO(BaseModel):
    id: str
    user_id: str
    team_id: Optional[str]
    query: str
    response: str
    tokens_saved: int
    model_used: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── /auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
