from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


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


def readiness_score(resume_score: int, linkedin_score: int, mocks_completed: int, hours_per_week: int) -> int:
    score = resume_score * 0.3 + linkedin_score * 0.2 + min(mocks_completed, 5) * 10 + min(hours_per_week, 15) * 2
    return min(int(score), 100)


def daily_schedule(hours_per_week: int) -> list[str]:
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    base = max(hours_per_week // len(days), 1)
    extra = hours_per_week % len(days)
    plan = []
    for idx, day in enumerate(days):
        hours = base + (1 if idx < extra else 0)
        plan.append(f"{day}: {hours} prep hour{'s' if hours != 1 else ''}")
    return plan


st.set_page_config(page_title="Gurukul Quick App", page_icon="🎯", layout="wide")

st.title("🎯 Gurukul Quick App")
st.caption("Prototype for personalized roadmap creation, resource mapping, scheduling, and interview readiness scoring.")

with st.sidebar:
    st.header("User Inputs")
    role = st.selectbox("Target role", ["SDE", "PM", "Data Analyst"])
    timeline_days = st.slider("Prep timeline (days)", min_value=14, max_value=90, value=30, step=7)
    hours_per_week = st.slider("Available prep hours per week", min_value=3, max_value=25, value=8)
    skill_level = st.selectbox("Current skill level", ["Beginner", "Intermediate", "Advanced"])
    resume_score = st.slider("Resume readiness", min_value=0, max_value=100, value=68)
    linkedin_score = st.slider("LinkedIn readiness", min_value=0, max_value=100, value=61)
    mocks_completed = st.slider("Mock exams & interviews completed", min_value=0, max_value=10, value=1)

weeks = max(timeline_days // 7, 2)
roadmap = build_roadmap(role, weeks, skill_level)
score = readiness_score(resume_score, linkedin_score, mocks_completed, hours_per_week)
resources = ROLE_RESOURCES[role]
schedule = daily_schedule(hours_per_week)

metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
metric_col_1.metric("Interview readiness", f"{score}/100")
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
    st.progress(score / 100)
    if score < 50:
        st.warning("Profile readiness is low. Prioritize resume updates and mentor feedback before increasing mock intensity.")
    elif score < 75:
        st.info("Profile readiness is improving. Continue profile updates alongside weekly mock interviews.")
    else:
        st.success("Profile readiness is strong. Shift more time toward mock interviews and salary negotiation support.")

    st.subheader("Mock Exams & Interviews")
    st.write(
        f"You have completed **{mocks_completed}** mock session{'s' if mocks_completed != 1 else ''}. "
        "Use feedback reports to target weak areas in the next roadmap block."
    )

    st.subheader("Salary Negotiation Support")
    st.write(
        "When readiness is above 70, add a final-week negotiation session covering offer benchmarking, "
        "email scripts, and peer comparisons."
    )
