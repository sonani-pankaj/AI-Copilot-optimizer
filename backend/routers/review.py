# See: specs/backend/review-endpoint.md
import json
import logging

from fastapi import APIRouter, Depends, HTTPException

from ..auth.jwt import TokenData, verify_token
from ..models.schemas import ReviewIssue, ReviewRequest, ReviewResponse
from ..services import openai_service, sanitizer

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ReviewResponse)
async def review(
    req: ReviewRequest,
    token: TokenData = Depends(verify_token),
) -> ReviewResponse:
    """Analyze a git diff and return structured bugs/perf/security findings."""

    # Sanitize and truncate
    diff = sanitizer.sanitize(req.diff)[:4_000]
    if not diff.strip():
        return ReviewResponse(summary="Empty diff provided.")

    # Build the prompt
    parts = [f"Git diff:\n```\n{diff}\n```"]
    if req.pr_title:
        parts.insert(0, f"PR Title: {req.pr_title}")
    if req.pr_description:
        parts.insert(1, f"PR Description: {req.pr_description}")
    prompt = "\n\n".join(parts)

    try:
        raw, _ = await openai_service.complete(prompt, "REVIEW")
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Review service unavailable")

    # Parse JSON response
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("OpenAI returned non-JSON for review (hash omitted for privacy)")
        raise HTTPException(status_code=502, detail="Review service returned invalid response")

    def _parse_issues(items: list) -> list[ReviewIssue]:
        result = []
        for item in items or []:
            try:
                result.append(
                    ReviewIssue(
                        severity=item.get("severity", "LOW"),
                        category=item.get("category", "bug"),
                        description=item.get("description", ""),
                        line_hint=item.get("line_hint"),
                    )
                )
            except Exception:
                pass
        return result

    return ReviewResponse(
        bugs=_parse_issues(data.get("bugs", [])),
        performance=_parse_issues(data.get("performance", [])),
        security=_parse_issues(data.get("security", [])),
        summary=data.get("summary", "Review complete."),
    )
