from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from profile_readiness import (
    CATEGORY_LABELS,
    HISTORY_SESSION_KEY,
    ProfileReadinessInput,
    append_history_entry,
    calculate_readiness,
    generate_recommendations,
    latest_score_delta,
    recent_history_entries,
)


@dataclass(frozen=True)
class RoadmapWeek:
    title: str
    focus: str
    milestone: str


ROLE_RESOURCES = {
    "SDE": [
        "NeetCode practice set",
        "System design primer",
        "Behavioral interview story bank",
    ],
    "PM": [
        "Product sense case prompts",
        "Metrics and experimentation guide",
        "Stakeholder communication framework",
    ],
    "Data Analyst": [
        "SQL interview drills",
        "Dashboard portfolio review checklist",
        "Business case storytelling guide",
    ],
}


def build_roadmap(role: str, weeks: int, skill_level: str) -> list[RoadmapWeek]:
    phase_templates = [
        ("Foundation", "Build baseline concepts and problem-solving rhythm."),
        ("Practice", "Increase repetition with timed drills and mock exercises."),
        ("Refinement", "Close gaps using feedback and targeted review."),
        ("Readiness", "Simulate real interviews and finalize execution habits."),
    ]
    skill_adjustment = {
        "Beginner": "Spend more time on fundamentals before mock interviews.",
        "Intermediate": "Balance review with increasing interview pressure.",
        "Advanced": "Bias toward mocks, analytics, and negotiation prep.",
    }[skill_level]

    roadmap = []
    for index in range(weeks):
        phase_title, phase_focus = phase_templates[min(index * len(phase_templates) // weeks, len(phase_templates) - 1)]
        roadmap.append(
            RoadmapWeek(
                title=f"Week {index + 1}: {phase_title}",
                focus=f"{role} prep focus: {phase_focus} {skill_adjustment}",
                milestone=f"Complete a measurable checkpoint for {role} by the end of week {index + 1}.",
            )
        )
    return roadmap


def daily_schedule(hours_per_week: int) -> list[str]:
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    base = max(hours_per_week // len(days), 1)
    extra = hours_per_week % len(days)
    plan = []
    for idx, day in enumerate(days):
        hours = base + (1 if idx < extra else 0)
        plan.append(f"{day}: {hours} prep hour{'s' if hours != 1 else ''}")
    return plan


def profile_readiness_snapshot(
    *,
    resume_uploaded: bool,
    resume_parseable: bool,
    ats_score: int | None,
    formatting_score: int | None,
    impact_score: int | None,
    linkedin_feedback_available: bool,
    linkedin_score: int | None,
    linkedin_confirmed_missing: bool,
    mentor_review_available: bool,
    mentor_review_score: int | None,
) -> tuple[tuple[str, int | bool | None], ...]:
    return (
        ("resume_uploaded", resume_uploaded),
        ("resume_parseable", resume_parseable),
        ("ats_score", ats_score),
        ("formatting_score", formatting_score),
        ("impact_score", impact_score),
        ("linkedin_feedback_available", linkedin_feedback_available),
        ("linkedin_score", linkedin_score),
        ("linkedin_confirmed_missing", linkedin_confirmed_missing),
        ("mentor_review_available", mentor_review_available),
        ("mentor_review_score", mentor_review_score),
    )


def history_trigger_reason(
    previous_snapshot: tuple[tuple[str, int | bool | None], ...] | None,
    current_snapshot: tuple[tuple[str, int | bool | None], ...],
) -> str:
    if previous_snapshot is None:
        return "initial_calculation"

    previous = dict(previous_snapshot)
    current = dict(current_snapshot)
    changed_inputs = {
        key
        for key, value in current.items()
        if previous.get(key) != value
    }
    changed_groups = []
    if changed_inputs & {"resume_uploaded", "resume_parseable", "ats_score", "formatting_score", "impact_score"}:
        changed_groups.append("resume")
    if changed_inputs & {"linkedin_feedback_available", "linkedin_score", "linkedin_confirmed_missing"}:
        changed_groups.append("linkedin")
    if changed_inputs & {"mentor_review_available", "mentor_review_score"}:
        changed_groups.append("mentor_recruiter_review")

    if not changed_groups:
        return "profile_recalculated"
    return f"{'_'.join(changed_groups)}_update"


def score_delta_label(delta: int | None) -> str | None:
    if delta is None:
        return None
    if delta > 0:
        return f"+{delta} since previous score"
    return f"{delta} since previous score"


def history_entry_line(entry) -> str:
    score_display = "Not scored" if entry.score is None else f"{entry.score}/100"
    band_display = entry.readiness_band or "Resume needed"
    gap_display = CATEGORY_LABELS.get(entry.top_gap_category, "No top gap")
    review_display = "human reviewed" if entry.human_reviewed else "human review default"
    provisional_display = "provisional" if entry.provisional else "final"
    trigger_display = entry.trigger_reason.replace("_", " ")
    return (
        f"- {entry.timestamp}: {score_display} · {band_display} · "
        f"top gap: {gap_display} · {provisional_display} · "
        f"{review_display} · {trigger_display}"
    )


st.set_page_config(page_title="Gurukul Quick App", page_icon="🎯", layout="wide")

st.title("🎯 Gurukul Quick App")
st.caption("Prototype for personalized roadmap creation, resource mapping, scheduling, and profile readiness scoring.")

with st.sidebar:
    st.header("User Inputs")
    role = st.selectbox("Target role", ["SDE", "PM", "Data Analyst"])
    timeline_days = st.slider("Prep timeline (days)", min_value=14, max_value=90, value=30, step=7)
    hours_per_week = st.slider("Available prep hours per week", min_value=3, max_value=25, value=8)
    skill_level = st.selectbox("Current skill level", ["Beginner", "Intermediate", "Advanced"])

    st.header("Profile Readiness Inputs")
    resume_uploaded = st.checkbox("Resume imported for scoring", value=True)
    if resume_uploaded:
        resume_parseable = st.checkbox("Resume can be parsed", value=True)
        ats_score = st.slider("Resume ATS compliance", min_value=0, max_value=100, value=68)
        formatting_score = st.slider("Resume formatting", min_value=0, max_value=100, value=72)
        impact_score = (
            st.slider("Resume impact", min_value=0, max_value=100, value=64)
            if resume_parseable
            else None
        )
    else:
        resume_parseable = False
        ats_score = None
        formatting_score = None
        impact_score = None

    linkedin_feedback_available = st.checkbox("LinkedIn feedback available", value=True)
    if linkedin_feedback_available:
        linkedin_score = st.slider("LinkedIn profile feedback", min_value=0, max_value=100, value=61)
        linkedin_confirmed_missing = False
    else:
        linkedin_score = None
        linkedin_confirmed_missing = st.checkbox("User skipped LinkedIn feedback", value=False)

    mentor_review_available = st.checkbox("Mentor/recruiter review provided", value=False)
    mentor_review_score = (
        st.slider("Mentor/recruiter review", min_value=0, max_value=100, value=70)
        if mentor_review_available
        else None
    )
    mocks_completed = st.slider("Mock exams & interviews completed", min_value=0, max_value=10, value=1)

weeks = max(timeline_days // 7, 2)
roadmap = build_roadmap(role, weeks, skill_level)
readiness = calculate_readiness(
    ProfileReadinessInput(
        ats_score=ats_score,
        formatting_score=formatting_score,
        impact_score=impact_score,
        linkedin_score=linkedin_score,
        mentor_review_score=mentor_review_score,
        resume_uploaded=resume_uploaded,
        resume_parseable=resume_parseable,
        linkedin_confirmed_missing=linkedin_confirmed_missing,
    )
)
readiness_snapshot = profile_readiness_snapshot(
    resume_uploaded=resume_uploaded,
    resume_parseable=resume_parseable,
    ats_score=ats_score,
    formatting_score=formatting_score,
    impact_score=impact_score,
    linkedin_feedback_available=linkedin_feedback_available,
    linkedin_score=linkedin_score,
    linkedin_confirmed_missing=linkedin_confirmed_missing,
    mentor_review_available=mentor_review_available,
    mentor_review_score=mentor_review_score,
)
previous_readiness_snapshot = st.session_state.get("profile_readiness_history_snapshot")
if previous_readiness_snapshot != readiness_snapshot:
    append_history_entry(
        st.session_state,
        readiness,
        trigger_reason=history_trigger_reason(previous_readiness_snapshot, readiness_snapshot),
    )
    st.session_state["profile_readiness_history_snapshot"] = readiness_snapshot
readiness_history = recent_history_entries(st.session_state, limit=5)
readiness_score_delta = latest_score_delta(st.session_state.get(HISTORY_SESSION_KEY, []))
recommendations = generate_recommendations(readiness)
resources = ROLE_RESOURCES[role]
schedule = daily_schedule(hours_per_week)

metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
metric_col_1.metric(
    "Profile readiness",
    f"{readiness.score}/100" if readiness.score is not None else "Not scored",
    score_delta_label(readiness_score_delta) or readiness.readiness_band or "Resume needed",
)
metric_col_2.metric("Roadmap length", f"{weeks} weeks")
metric_col_3.metric("Resource matches", len(resources))
metric_col_4.metric("Weekly prep hours", hours_per_week)

left_col, right_col = st.columns([1.4, 1])

with left_col:
    st.subheader("Personalized Roadmap Creation")
    for week in roadmap:
        with st.container(border=True):
            st.markdown(f"**{week.title}**")
            st.write(week.focus)
            st.caption(week.milestone)

    st.subheader("Map Roadmap Items to Resources")
    for resource in resources:
        st.write(f"- {resource}")

with right_col:
    st.subheader("Auto-Schedule Sessions Within Timeline")
    for item in schedule:
        st.write(f"- {item}")

    st.subheader("Resume & LinkedIn Optimization")
    if readiness.score is None:
        st.info("Import or upload a resume to calculate profile readiness.")
    else:
        st.progress(readiness.score / 100)
        st.write(f"**Readiness band:** {readiness.readiness_band}")
        if readiness.top_gap_label:
            top_gap = readiness.weighted_gaps[readiness.top_gap_category]
            st.write(f"**Top gap:** {readiness.top_gap_label} ({top_gap:g} weighted points)")

        if readiness.provisional:
            st.warning("This score is provisional because one or more profile readiness inputs are incomplete.")
        elif readiness.score < 65:
            st.warning("Profile readiness has important gaps. Prioritize profile updates before increasing mock intensity.")
        elif readiness.score < 80:
            st.info("Profile readiness is improving. Continue profile updates alongside weekly mock interviews.")
        else:
            st.success("Profile readiness is strong. Shift more time toward mock interviews and salary negotiation support.")

        if readiness.human_reviewed:
            st.caption("Includes mentor/recruiter review input.")
        else:
            st.caption("Mentor/recruiter review uses a neutral default until human feedback is provided.")

    st.markdown("**Recent readiness history**")
    if readiness_score_delta is None:
        st.caption("No previous scored recalculation yet.")
    else:
        st.caption(f"Score change from the previous scored recalculation: {readiness_score_delta:+d}.")
    for history_entry in readiness_history:
        st.write(history_entry_line(history_entry))

    st.markdown("**Recommended next actions**")
    for recommendation in recommendations:
        st.write(f"{recommendation.rank}. {recommendation.action}")

    with st.expander("Category breakdown"):
        for category, label in CATEGORY_LABELS.items():
            score_value = readiness.category_scores[category]
            score_display = "Incomplete" if score_value is None else f"{score_value}/100"
            gap = readiness.weighted_gaps[category]
            st.write(f"**{label}:** {score_display} · weighted gap {gap:g}")

    st.subheader("Mock Exams & Interviews")
    st.write(
        f"You have completed **{mocks_completed}** mock session{'s' if mocks_completed != 1 else ''}. "
        "Use feedback reports to target weak areas in the next roadmap block."
    )

    st.subheader("Salary Negotiation Support")
    if readiness.score is not None and readiness.score > 70:
        st.write(
            "Profile readiness is above 70. Add a final-week negotiation session covering offer benchmarking, "
            "email scripts, and peer comparisons."
        )
    else:
        st.write(
            "Raise profile readiness above 70 before adding a final-week negotiation session with offer benchmarking, "
            "email scripts, and peer comparisons."
        )
