from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Sequence
from uuid import uuid4

from .recommendations import Recommendation
from .scoring import ProfileReadinessResult


SCHEMA_VERSION = 1

_PRIVATE_FIELD_MARKERS = (
    "raw_resume",
    "resume_text",
    "raw_linkedin",
    "linkedin_text",
    "contact_information",
    "contact_info",
    "email",
    "phone",
    "external_profile_url",
    "profile_url",
    "mentor_notes",
    "recruiter_notes",
)


def build_recalculation_requested_event(
    *,
    user_id: str,
    profile_id: str,
    source: str,
    trigger_event_id: str,
    trigger_reason: str,
    changed_inputs: Iterable[str],
    event_id: str | None = None,
    occurred_at: datetime | str | None = None,
) -> dict:
    event = _base_event(
        "profile_readiness_recalculation_requested",
        user_id,
        profile_id,
        source,
        event_id,
        occurred_at,
    )
    event.update(
        {
            "trigger_event_id": trigger_event_id,
            "trigger_reason": trigger_reason,
            "changed_inputs": _safe_changed_inputs(changed_inputs),
        }
    )
    return event


def build_score_recalculated_event(
    *,
    user_id: str,
    profile_id: str,
    source: str,
    score_id: str,
    previous_result: ProfileReadinessResult | None,
    new_result: ProfileReadinessResult,
    event_id: str | None = None,
    occurred_at: datetime | str | None = None,
) -> dict:
    previous_score = previous_result.score if previous_result else None
    new_score = new_result.score
    score_delta = (
        new_score - previous_score
        if previous_score is not None and new_score is not None
        else None
    )

    event = _base_event(
        "profile_readiness_score_recalculated",
        user_id,
        profile_id,
        source,
        event_id,
        occurred_at,
    )
    event.update(
        {
            "score_id": score_id,
            "previous_score": previous_score,
            "new_score": new_score,
            "score_delta": score_delta,
            "previous_band": previous_result.readiness_band if previous_result else None,
            "new_band": new_result.readiness_band,
            "category_scores": dict(new_result.category_scores),
            "category_weights": dict(new_result.category_weights),
            "provisional_score": new_result.provisional,
            "human_reviewed": new_result.human_reviewed,
            "lowest_scoring_category": new_result.lowest_scoring_category,
            "calculation_version": new_result.calculation_version,
        }
    )
    return event


def build_recommendations_generated_event(
    *,
    user_id: str,
    profile_id: str,
    source: str,
    score_id: str,
    recommendations: Sequence[Recommendation],
    generation_reason: str,
    confidence: str,
    event_id: str | None = None,
    occurred_at: datetime | str | None = None,
) -> dict:
    event = _base_event(
        "profile_readiness_recommendations_generated",
        user_id,
        profile_id,
        source,
        event_id,
        occurred_at,
    )
    event.update(
        {
            "score_id": score_id,
            "recommendation_count": len(recommendations),
            "top_category": recommendations[0].category if recommendations else None,
            "generation_reason": generation_reason,
            "confidence": confidence,
        }
    )
    return event


def build_recommendation_viewed_event(
    *,
    user_id: str,
    profile_id: str,
    source: str,
    recommendation: Recommendation,
    score_id: str,
    event_id: str | None = None,
    occurred_at: datetime | str | None = None,
) -> dict:
    event = _base_event(
        "profile_readiness_recommendation_viewed",
        user_id,
        profile_id,
        source,
        event_id,
        occurred_at,
    )
    event.update(
        {
            "recommendation_id": recommendation.recommendation_id,
            "score_id": score_id,
            "category": recommendation.category,
            "rank": recommendation.rank,
            "recommendation_type": recommendation.recommendation_type,
        }
    )
    return event


def build_recommendation_started_event(
    *,
    user_id: str,
    profile_id: str,
    source: str,
    recommendation: Recommendation,
    score_id: str,
    action_type: str,
    event_id: str | None = None,
    occurred_at: datetime | str | None = None,
) -> dict:
    event = _base_event(
        "profile_readiness_recommendation_started",
        user_id,
        profile_id,
        source,
        event_id,
        occurred_at,
    )
    event.update(
        {
            "recommendation_id": recommendation.recommendation_id,
            "score_id": score_id,
            "category": recommendation.category,
            "action_type": action_type,
        }
    )
    return event


def build_recommendation_completed_event(
    *,
    user_id: str,
    profile_id: str,
    source: str,
    recommendation: Recommendation,
    score_id: str,
    completion_source: str,
    recalculation_requested: bool,
    event_id: str | None = None,
    occurred_at: datetime | str | None = None,
) -> dict:
    event = _base_event(
        "profile_readiness_recommendation_completed",
        user_id,
        profile_id,
        source,
        event_id,
        occurred_at,
    )
    event.update(
        {
            "recommendation_id": recommendation.recommendation_id,
            "score_id": score_id,
            "category": recommendation.category,
            "completion_source": completion_source,
            "recalculation_requested": recalculation_requested,
        }
    )
    return event


def _base_event(
    event_name: str,
    user_id: str,
    profile_id: str,
    source: str,
    event_id: str | None,
    occurred_at: datetime | str | None,
) -> dict:
    return {
        "event_name": event_name,
        "event_id": event_id or str(uuid4()),
        "user_id": user_id,
        "profile_id": profile_id,
        "occurred_at": _format_occurred_at(occurred_at),
        "source": source,
        "schema_version": SCHEMA_VERSION,
    }


def _format_occurred_at(occurred_at: datetime | str | None) -> str:
    if occurred_at is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if isinstance(occurred_at, datetime):
        timestamp = occurred_at
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.isoformat()
    return occurred_at


def _safe_changed_inputs(changed_inputs: Iterable[str]) -> list[str]:
    safe_inputs = []
    for changed_input in changed_inputs:
        if not isinstance(changed_input, str):
            continue
        normalized = changed_input.strip()
        if normalized and not _looks_private_field(normalized):
            safe_inputs.append(normalized)
    return safe_inputs


def _looks_private_field(field_name: str) -> bool:
    normalized = field_name.lower()
    return any(marker in normalized for marker in _PRIVATE_FIELD_MARKERS)
