from __future__ import annotations

from dataclasses import dataclass

from .scoring import (
    CATEGORY_ATS,
    CATEGORY_FORMATTING,
    CATEGORY_IMPACT,
    CATEGORY_LABELS,
    CATEGORY_LINKEDIN,
    CATEGORY_MENTOR_REVIEW,
    ProfileReadinessResult,
    rank_categories_by_weighted_gap,
)


@dataclass(frozen=True)
class Recommendation:
    recommendation_id: str
    category: str
    category_label: str
    rank: int
    action: str
    rationale: str
    recommendation_type: str


def generate_recommendations(
    result: ProfileReadinessResult, limit: int = 3
) -> list[Recommendation]:
    if result.score is None:
        return [
            Recommendation(
                recommendation_id="profile-readiness-1-resume-import",
                category=CATEGORY_ATS,
                category_label=CATEGORY_LABELS[CATEGORY_ATS],
                rank=1,
                action="Import or upload a parseable resume to start profile readiness scoring.",
                rationale="No resume is available, so Gurukul cannot calculate the documented readiness score.",
                recommendation_type="resume_import",
            )
        ]

    recommendations: list[Recommendation] = []
    for category in rank_categories_by_weighted_gap(result):
        if result.weighted_gaps[category] <= 0:
            continue
        rank = len(recommendations) + 1
        recommendations.append(
            Recommendation(
                recommendation_id=f"profile-readiness-{rank}-{category}",
                category=category,
                category_label=CATEGORY_LABELS[category],
                rank=rank,
                action=_action_for(category, result.category_statuses[category]),
                rationale=(
                    f"{CATEGORY_LABELS[category]} has the largest remaining weighted gap "
                    f"at rank {rank}."
                ),
                recommendation_type=_recommendation_type_for(category),
            )
        )
        if len(recommendations) >= limit:
            break

    return recommendations


def _action_for(category: str, status: str) -> str:
    if category == CATEGORY_ATS:
        if status == "capped_unparseable":
            return "Upload a parseable resume file and rerun ATS compliance checks."
        return "Fix ATS blockers: parseability, required sections, contact presence, and role keywords."
    if category == CATEGORY_FORMATTING:
        return "Standardize section order, bullet style, page length, tense, and readability."
    if category == CATEGORY_IMPACT:
        if status == "withheld_unparseable":
            return "Upload a readable resume so impact scoring can evaluate accomplishments."
        return "Rewrite weak bullets with quantified outcomes, action verbs, scope, and role relevance."
    if category == CATEGORY_LINKEDIN:
        if status == "missing":
            return "Add or skip LinkedIn feedback so the score is no longer provisional."
        return "Align LinkedIn headline, About, experience, skills, and projects with the target role."
    if category == CATEGORY_MENTOR_REVIEW:
        if status == "defaulted":
            return "Request an optional mentor/recruiter review to add human context."
        return "Address the mentor/recruiter priority gap before the next recalculation."
    raise ValueError(f"unknown profile readiness category: {category}")


def _recommendation_type_for(category: str) -> str:
    if category == CATEGORY_MENTOR_REVIEW:
        return "human_review"
    if category == CATEGORY_LINKEDIN:
        return "linkedin_update"
    if category == CATEGORY_ATS:
        return "resume_ats_update"
    return "resume_update"
