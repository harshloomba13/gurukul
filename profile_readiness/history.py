from __future__ import annotations

from collections.abc import MutableMapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from .scoring import ProfileReadinessResult


HISTORY_SESSION_KEY = "profile_readiness_score_history"
HISTORY_STORAGE_POLICY = "session"
DEFAULT_TRIGGER_REASON = "profile_recalculated"

ALLOWED_TRIGGER_REASONS = frozenset(
    {
        DEFAULT_TRIGGER_REASON,
        "initial_calculation",
        "resume_update",
        "linkedin_update",
        "mentor_recruiter_review_update",
        "resume_linkedin_update",
        "resume_mentor_recruiter_review_update",
        "linkedin_mentor_recruiter_review_update",
        "resume_linkedin_mentor_recruiter_review_update",
    }
)


@dataclass(frozen=True)
class ProfileReadinessHistoryEntry:
    score: int | None
    readiness_band: str | None
    top_gap_category: str | None
    provisional: bool
    human_reviewed: bool
    trigger_reason: str
    timestamp: str

    def as_payload(self) -> dict[str, Any]:
        return asdict(self)


def append_history_entry(
    session_state: MutableMapping[str, Any],
    result: ProfileReadinessResult,
    *,
    trigger_reason: str | None = DEFAULT_TRIGGER_REASON,
    timestamp: datetime | str | None = None,
    session_key: str = HISTORY_SESSION_KEY,
) -> ProfileReadinessHistoryEntry:
    entry = build_history_entry(result, trigger_reason=trigger_reason, timestamp=timestamp)
    history = list(session_state.get(session_key, []))
    history.append(entry)
    session_state[session_key] = history
    return entry


def build_history_entry(
    result: ProfileReadinessResult,
    *,
    trigger_reason: str | None = DEFAULT_TRIGGER_REASON,
    timestamp: datetime | str | None = None,
) -> ProfileReadinessHistoryEntry:
    return ProfileReadinessHistoryEntry(
        score=result.score,
        readiness_band=result.readiness_band,
        top_gap_category=result.top_gap_category,
        provisional=result.provisional,
        human_reviewed=result.human_reviewed,
        trigger_reason=_safe_trigger_reason(trigger_reason),
        timestamp=_format_timestamp(timestamp),
    )


def recent_history_entries(
    session_state: MutableMapping[str, Any],
    *,
    limit: int = 5,
    session_key: str = HISTORY_SESSION_KEY,
) -> list[ProfileReadinessHistoryEntry]:
    if limit <= 0:
        return []
    history = list(session_state.get(session_key, []))
    return history[-limit:]


def latest_score_delta(entries: Sequence[ProfileReadinessHistoryEntry]) -> int | None:
    if not entries:
        return None

    latest_entry = entries[-1]
    if latest_entry.score is None:
        return None

    for previous_entry in reversed(entries[:-1]):
        if previous_entry.score is not None:
            return latest_entry.score - previous_entry.score
    return None


def _format_timestamp(timestamp: datetime | str | None) -> str:
    if timestamp is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if isinstance(timestamp, datetime):
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.isoformat()
    return timestamp


def _safe_trigger_reason(trigger_reason: str | None) -> str:
    if not isinstance(trigger_reason, str):
        return DEFAULT_TRIGGER_REASON
    normalized = trigger_reason.strip().lower()
    if normalized not in ALLOWED_TRIGGER_REASONS:
        return DEFAULT_TRIGGER_REASON
    return normalized
