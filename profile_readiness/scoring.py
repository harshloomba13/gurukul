from __future__ import annotations

from dataclasses import dataclass
from math import floor


CATEGORY_ATS = "resume_ats_compliance"
CATEGORY_FORMATTING = "resume_formatting"
CATEGORY_IMPACT = "resume_impact"
CATEGORY_LINKEDIN = "linkedin_profile_feedback"
CATEGORY_MENTOR_REVIEW = "mentor_recruiter_review"

CATEGORY_ORDER = (
    CATEGORY_ATS,
    CATEGORY_FORMATTING,
    CATEGORY_IMPACT,
    CATEGORY_LINKEDIN,
    CATEGORY_MENTOR_REVIEW,
)

CATEGORY_LABELS = {
    CATEGORY_ATS: "Resume ATS compliance",
    CATEGORY_FORMATTING: "Resume formatting",
    CATEGORY_IMPACT: "Resume impact",
    CATEGORY_LINKEDIN: "LinkedIn profile feedback",
    CATEGORY_MENTOR_REVIEW: "Mentor/recruiter review",
}

CATEGORY_WEIGHTS = {
    CATEGORY_ATS: 0.30,
    CATEGORY_FORMATTING: 0.15,
    CATEGORY_IMPACT: 0.25,
    CATEGORY_LINKEDIN: 0.20,
    CATEGORY_MENTOR_REVIEW: 0.10,
}

CALCULATION_VERSION = "profile_readiness_v1"
MENTOR_REVIEW_DEFAULT_SCORE = 50


@dataclass(frozen=True)
class ProfileReadinessInput:
    ats_score: int | None = None
    formatting_score: int | None = None
    impact_score: int | None = None
    linkedin_score: int | None = None
    mentor_review_score: int | None = None
    resume_uploaded: bool = True
    resume_parseable: bool = True
    linkedin_confirmed_missing: bool = False
    low_confidence: bool = False


@dataclass(frozen=True)
class ProfileReadinessResult:
    score: int | None
    unrounded_score: float | None
    readiness_band: str | None
    category_scores: dict[str, int | None]
    category_statuses: dict[str, str]
    category_weights: dict[str, float]
    weighted_gaps: dict[str, float]
    top_gap_category: str | None
    top_gap_label: str | None
    lowest_scoring_category: str | None
    provisional: bool
    human_reviewed: bool
    calculation_version: str = CALCULATION_VERSION


def calculate_readiness(profile: ProfileReadinessInput) -> ProfileReadinessResult:
    """Calculate the first-prototype profile readiness score from GURU-104 docs."""
    if not profile.resume_uploaded:
        return _empty_resume_result(profile)

    category_scores: dict[str, int | None] = {}
    category_statuses: dict[str, str] = {}

    ats_score = _normalize_score(profile.ats_score, default=20 if not profile.resume_parseable else None)
    if not profile.resume_parseable:
        ats_score = min(ats_score if ats_score is not None else 20, 20)
        category_statuses[CATEGORY_ATS] = "capped_unparseable"
    else:
        category_statuses[CATEGORY_ATS] = "scored" if ats_score is not None else "missing"
    category_scores[CATEGORY_ATS] = ats_score

    formatting_score = _normalize_score(profile.formatting_score)
    category_scores[CATEGORY_FORMATTING] = formatting_score
    category_statuses[CATEGORY_FORMATTING] = "scored" if formatting_score is not None else "missing"

    if profile.resume_parseable:
        impact_score = _normalize_score(profile.impact_score)
        category_scores[CATEGORY_IMPACT] = impact_score
        category_statuses[CATEGORY_IMPACT] = "scored" if impact_score is not None else "missing"
    else:
        category_scores[CATEGORY_IMPACT] = None
        category_statuses[CATEGORY_IMPACT] = "withheld_unparseable"

    linkedin_score = _normalize_score(profile.linkedin_score)
    if linkedin_score is None and profile.linkedin_confirmed_missing:
        linkedin_score = 0
        category_statuses[CATEGORY_LINKEDIN] = "confirmed_missing"
    else:
        category_statuses[CATEGORY_LINKEDIN] = "scored" if linkedin_score is not None else "missing"
    category_scores[CATEGORY_LINKEDIN] = linkedin_score

    mentor_review_score = _normalize_score(profile.mentor_review_score)
    human_reviewed = mentor_review_score is not None
    if mentor_review_score is None:
        mentor_review_score = MENTOR_REVIEW_DEFAULT_SCORE
        category_statuses[CATEGORY_MENTOR_REVIEW] = "defaulted"
    else:
        category_statuses[CATEGORY_MENTOR_REVIEW] = "scored"
    category_scores[CATEGORY_MENTOR_REVIEW] = mentor_review_score

    weighted_gaps = _weighted_gaps(category_scores)
    missing_weight = sum(
        CATEGORY_WEIGHTS[category]
        for category, score in category_scores.items()
        if score is None
    )
    available_weight = 1 - missing_weight
    weighted_total = sum(
        (score or 0) * CATEGORY_WEIGHTS[category]
        for category, score in category_scores.items()
        if score is not None
    )

    unrounded_score = weighted_total / available_weight if available_weight > 0 else None
    score = _round_score(unrounded_score) if unrounded_score is not None else None
    readiness_band = readiness_band_for_score(score) if score is not None else None
    top_gap_category = _top_gap_category(weighted_gaps)

    provisional = profile.low_confidence or any(score is None for score in category_scores.values())

    return ProfileReadinessResult(
        score=score,
        unrounded_score=round(unrounded_score, 4) if unrounded_score is not None else None,
        readiness_band=readiness_band,
        category_scores=category_scores,
        category_statuses=category_statuses,
        category_weights=dict(CATEGORY_WEIGHTS),
        weighted_gaps=weighted_gaps,
        top_gap_category=top_gap_category,
        top_gap_label=CATEGORY_LABELS[top_gap_category] if top_gap_category else None,
        lowest_scoring_category=_lowest_scoring_category(category_scores),
        provisional=provisional,
        human_reviewed=human_reviewed,
    )


def readiness_band_for_score(score: int) -> str:
    if score < 0 or score > 100:
        raise ValueError("readiness score must be between 0 and 100")
    if score <= 39:
        return "Not ready"
    if score <= 64:
        return "Needs work"
    if score <= 79:
        return "Approaching ready"
    if score <= 89:
        return "Ready"
    return "Strong"


def rank_categories_by_weighted_gap(result: ProfileReadinessResult) -> list[str]:
    return sorted(
        CATEGORY_ORDER,
        key=lambda category: (
            result.weighted_gaps[category],
            CATEGORY_WEIGHTS[category],
            -CATEGORY_ORDER.index(category),
        ),
        reverse=True,
    )


def _empty_resume_result(profile: ProfileReadinessInput) -> ProfileReadinessResult:
    category_scores = {category: None for category in CATEGORY_ORDER}
    category_statuses = {category: "missing" for category in CATEGORY_ORDER}
    weighted_gaps = _weighted_gaps(category_scores)
    top_gap_category = _top_gap_category(weighted_gaps)
    return ProfileReadinessResult(
        score=None,
        unrounded_score=None,
        readiness_band=None,
        category_scores=category_scores,
        category_statuses=category_statuses,
        category_weights=dict(CATEGORY_WEIGHTS),
        weighted_gaps=weighted_gaps,
        top_gap_category=top_gap_category,
        top_gap_label=CATEGORY_LABELS[top_gap_category] if top_gap_category else None,
        lowest_scoring_category=None,
        provisional=True,
        human_reviewed=profile.mentor_review_score is not None,
    )


def _normalize_score(value: int | None, default: int | None = None) -> int | None:
    if value is None:
        value = default
    if value is None:
        return None
    return max(0, min(100, int(value)))


def _round_score(value: float) -> int:
    return max(0, min(100, floor(value + 0.5)))


def _weighted_gaps(category_scores: dict[str, int | None]) -> dict[str, float]:
    gaps = {}
    for category in CATEGORY_ORDER:
        score = category_scores[category]
        category_score = 0 if score is None else score
        gaps[category] = round((100 - category_score) * CATEGORY_WEIGHTS[category], 2)
    return gaps


def _top_gap_category(weighted_gaps: dict[str, float]) -> str | None:
    if not weighted_gaps:
        return None
    return max(
        CATEGORY_ORDER,
        key=lambda category: (
            weighted_gaps[category],
            CATEGORY_WEIGHTS[category],
            -CATEGORY_ORDER.index(category),
        ),
    )


def _lowest_scoring_category(category_scores: dict[str, int | None]) -> str | None:
    scored_categories = [
        category for category in CATEGORY_ORDER if category_scores[category] is not None
    ]
    if not scored_categories:
        return None
    return min(scored_categories, key=lambda category: category_scores[category] or 0)
