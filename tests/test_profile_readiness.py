from __future__ import annotations

import unittest
from datetime import datetime, timezone

from profile_readiness import (
    HISTORY_SESSION_KEY,
    ProfileReadinessInput,
    append_history_entry,
    build_recalculation_requested_event,
    build_history_entry,
    build_recommendation_completed_event,
    build_recommendation_started_event,
    build_recommendation_viewed_event,
    build_recommendations_generated_event,
    build_score_recalculated_event,
    calculate_readiness,
    generate_recommendations,
    latest_score_delta,
    readiness_band_for_score,
    recent_history_entries,
)
from profile_readiness.scoring import (
    CATEGORY_ATS,
    CATEGORY_FORMATTING,
    CATEGORY_IMPACT,
    CATEGORY_LINKEDIN,
    CATEGORY_MENTOR_REVIEW,
)


class ProfileReadinessTests(unittest.TestCase):
    def test_weighted_score_calculation_and_top_gap(self) -> None:
        result = calculate_readiness(
            ProfileReadinessInput(
                ats_score=80,
                formatting_score=70,
                impact_score=60,
                linkedin_score=50,
                mentor_review_score=90,
            )
        )

        self.assertEqual(result.score, 69)
        self.assertEqual(result.unrounded_score, 68.5)
        self.assertEqual(result.readiness_band, "Approaching ready")
        self.assertFalse(result.provisional)
        self.assertTrue(result.human_reviewed)
        self.assertEqual(
            result.category_scores,
            {
                CATEGORY_ATS: 80,
                CATEGORY_FORMATTING: 70,
                CATEGORY_IMPACT: 60,
                CATEGORY_LINKEDIN: 50,
                CATEGORY_MENTOR_REVIEW: 90,
            },
        )
        self.assertEqual(result.weighted_gaps[CATEGORY_IMPACT], 10)
        self.assertEqual(result.weighted_gaps[CATEGORY_LINKEDIN], 10)
        self.assertEqual(result.top_gap_category, CATEGORY_IMPACT)

    def test_readiness_bands_are_exact(self) -> None:
        bands = {
            0: "Not ready",
            39: "Not ready",
            40: "Needs work",
            64: "Needs work",
            65: "Approaching ready",
            79: "Approaching ready",
            80: "Ready",
            89: "Ready",
            90: "Strong",
            100: "Strong",
        }

        for score, expected_band in bands.items():
            with self.subTest(score=score):
                self.assertEqual(readiness_band_for_score(score), expected_band)

        with self.assertRaises(ValueError):
            readiness_band_for_score(-1)
        with self.assertRaises(ValueError):
            readiness_band_for_score(101)

    def test_missing_linkedin_feedback_makes_score_provisional(self) -> None:
        result = calculate_readiness(
            ProfileReadinessInput(
                ats_score=80,
                formatting_score=80,
                impact_score=80,
                linkedin_score=None,
            )
        )

        self.assertEqual(result.score, 76)
        self.assertTrue(result.provisional)
        self.assertFalse(result.human_reviewed)
        self.assertIsNone(result.category_scores[CATEGORY_LINKEDIN])
        self.assertEqual(result.weighted_gaps[CATEGORY_LINKEDIN], 20)
        self.assertEqual(result.top_gap_category, CATEGORY_LINKEDIN)

        recommendations = generate_recommendations(result)
        self.assertEqual(recommendations[0].category, CATEGORY_LINKEDIN)
        self.assertIn("Add or skip LinkedIn feedback", recommendations[0].action)

    def test_confirmed_missing_linkedin_is_scored_as_zero(self) -> None:
        result = calculate_readiness(
            ProfileReadinessInput(
                ats_score=80,
                formatting_score=80,
                impact_score=80,
                linkedin_score=None,
                linkedin_confirmed_missing=True,
            )
        )

        self.assertEqual(result.score, 61)
        self.assertFalse(result.provisional)
        self.assertEqual(result.category_scores[CATEGORY_LINKEDIN], 0)
        self.assertEqual(result.category_statuses[CATEGORY_LINKEDIN], "confirmed_missing")

    def test_human_reviewed_scoring_changes_review_state(self) -> None:
        unreviewed = calculate_readiness(
            ProfileReadinessInput(
                ats_score=80,
                formatting_score=80,
                impact_score=80,
                linkedin_score=80,
            )
        )
        reviewed = calculate_readiness(
            ProfileReadinessInput(
                ats_score=80,
                formatting_score=80,
                impact_score=80,
                linkedin_score=80,
                mentor_review_score=90,
            )
        )

        self.assertEqual(unreviewed.score, 77)
        self.assertFalse(unreviewed.human_reviewed)
        self.assertEqual(unreviewed.category_scores[CATEGORY_MENTOR_REVIEW], 50)
        self.assertEqual(reviewed.score, 81)
        self.assertEqual(reviewed.readiness_band, "Ready")
        self.assertTrue(reviewed.human_reviewed)
        self.assertEqual(reviewed.category_scores[CATEGORY_MENTOR_REVIEW], 90)

    def test_weighted_gap_ranking_drives_recommendation_ordering(self) -> None:
        result = calculate_readiness(
            ProfileReadinessInput(
                ats_score=90,
                formatting_score=40,
                impact_score=80,
                linkedin_score=20,
                mentor_review_score=50,
            )
        )

        recommendations = generate_recommendations(result)

        self.assertEqual(result.top_gap_category, CATEGORY_LINKEDIN)
        self.assertEqual([item.category for item in recommendations], [CATEGORY_LINKEDIN, CATEGORY_FORMATTING, CATEGORY_IMPACT])
        self.assertEqual([item.rank for item in recommendations], [1, 2, 3])

    def test_unparseable_resume_caps_ats_and_withholds_impact(self) -> None:
        result = calculate_readiness(
            ProfileReadinessInput(
                ats_score=80,
                formatting_score=70,
                impact_score=80,
                linkedin_score=70,
                resume_parseable=False,
            )
        )

        self.assertEqual(result.category_scores[CATEGORY_ATS], 20)
        self.assertEqual(result.category_statuses[CATEGORY_ATS], "capped_unparseable")
        self.assertIsNone(result.category_scores[CATEGORY_IMPACT])
        self.assertEqual(result.category_statuses[CATEGORY_IMPACT], "withheld_unparseable")
        self.assertTrue(result.provisional)

    def test_session_history_appends_and_returns_recent_entries_newest_last(self) -> None:
        session_state = {}
        first = calculate_readiness(
            ProfileReadinessInput(
                ats_score=50,
                formatting_score=50,
                impact_score=50,
                linkedin_score=50,
            )
        )
        second = calculate_readiness(
            ProfileReadinessInput(
                ats_score=70,
                formatting_score=60,
                impact_score=65,
                linkedin_score=55,
            )
        )
        third = calculate_readiness(
            ProfileReadinessInput(
                ats_score=80,
                formatting_score=75,
                impact_score=70,
                linkedin_score=80,
                mentor_review_score=90,
            )
        )

        append_history_entry(
            session_state,
            first,
            trigger_reason="initial_calculation",
            timestamp=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        )
        append_history_entry(
            session_state,
            second,
            trigger_reason="resume_update",
            timestamp=datetime(2026, 1, 2, 12, tzinfo=timezone.utc),
        )
        append_history_entry(
            session_state,
            third,
            trigger_reason="mentor_recruiter_review_update",
            timestamp=datetime(2026, 1, 3, 12, tzinfo=timezone.utc),
        )

        entries = recent_history_entries(session_state, limit=2)

        self.assertIn(HISTORY_SESSION_KEY, session_state)
        self.assertEqual([entry.score for entry in entries], [second.score, third.score])
        self.assertEqual(
            [entry.trigger_reason for entry in entries],
            ["resume_update", "mentor_recruiter_review_update"],
        )
        self.assertTrue(entries[-1].human_reviewed)

    def test_latest_score_delta_compares_to_previous_scored_entry(self) -> None:
        first = calculate_readiness(
            ProfileReadinessInput(
                ats_score=55,
                formatting_score=55,
                impact_score=55,
                linkedin_score=55,
            )
        )
        unscored = calculate_readiness(ProfileReadinessInput(resume_uploaded=False))
        latest = calculate_readiness(
            ProfileReadinessInput(
                ats_score=85,
                formatting_score=75,
                impact_score=80,
                linkedin_score=75,
            )
        )

        history = [
            build_history_entry(first, trigger_reason="initial_calculation"),
            build_history_entry(unscored, trigger_reason="resume_update"),
            build_history_entry(latest, trigger_reason="resume_update"),
        ]

        self.assertEqual(latest_score_delta(history), latest.score - first.score)
        self.assertIsNone(latest_score_delta(history[:1]))
        self.assertIsNone(latest_score_delta(history[:2]))

    def test_history_entries_are_privacy_safe(self) -> None:
        session_state = {}
        result = calculate_readiness(
            ProfileReadinessInput(
                ats_score=90,
                formatting_score=40,
                impact_score=80,
                linkedin_score=20,
                mentor_review_score=50,
            )
        )

        entry = append_history_entry(
            session_state,
            result,
            trigger_reason="resume_text",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        payload = entry.as_payload()

        self.assertEqual(
            set(payload),
            {
                "score",
                "readiness_band",
                "top_gap_category",
                "provisional",
                "human_reviewed",
                "trigger_reason",
                "timestamp",
            },
        )
        self.assertEqual(payload["trigger_reason"], "profile_recalculated")
        self.assertNotIn("category_scores", payload)
        self.assertNotIn("weighted_gaps", payload)

        stored_payload = repr(session_state).lower()
        for forbidden in (
            "resume_text",
            "linkedin_text",
            "external_profile_url",
            "mentor_notes",
            "recruiter_notes",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, stored_payload)

    def test_event_payloads_are_privacy_safe(self) -> None:
        occurred_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        result = calculate_readiness(
            ProfileReadinessInput(
                ats_score=90,
                formatting_score=40,
                impact_score=80,
                linkedin_score=20,
                mentor_review_score=50,
            )
        )
        recommendations = generate_recommendations(result)

        recalculation_requested = build_recalculation_requested_event(
            user_id="user-1",
            profile_id="profile-1",
            source="manual_edit",
            trigger_event_id="trigger-1",
            trigger_reason="profile_inputs_updated",
            changed_inputs=[
                "ats_score",
                "resume_text",
                "email",
                "external_profile_url",
                "mentor_notes",
                "target_role",
            ],
            event_id="event-1",
            occurred_at=occurred_at,
        )
        score_recalculated = build_score_recalculated_event(
            user_id="user-1",
            profile_id="profile-1",
            source="system_recalculation",
            score_id="score-1",
            previous_result=None,
            new_result=result,
            event_id="event-2",
            occurred_at=occurred_at,
        )
        recommendations_generated = build_recommendations_generated_event(
            user_id="user-1",
            profile_id="profile-1",
            source="system_recalculation",
            score_id="score-1",
            recommendations=recommendations,
            generation_reason="score_recalculated",
            confidence="standard",
            event_id="event-3",
            occurred_at=occurred_at,
        )
        recommendation_viewed = build_recommendation_viewed_event(
            user_id="user-1",
            profile_id="profile-1",
            source="manual_edit",
            recommendation=recommendations[0],
            score_id="score-1",
            event_id="event-4",
            occurred_at=occurred_at,
        )
        recommendation_started = build_recommendation_started_event(
            user_id="user-1",
            profile_id="profile-1",
            source="manual_edit",
            recommendation=recommendations[0],
            score_id="score-1",
            action_type="linkedin_update",
            event_id="event-5",
            occurred_at=occurred_at,
        )
        recommendation_completed = build_recommendation_completed_event(
            user_id="user-1",
            profile_id="profile-1",
            source="manual_edit",
            recommendation=recommendations[0],
            score_id="score-1",
            completion_source="user_marked_complete",
            recalculation_requested=True,
            event_id="event-6",
            occurred_at=occurred_at,
        )

        self.assertEqual(recalculation_requested["changed_inputs"], ["ats_score", "target_role"])
        self.assertEqual(score_recalculated["category_scores"][CATEGORY_LINKEDIN], 20)
        self.assertEqual(recommendations_generated["top_category"], CATEGORY_LINKEDIN)
        self.assertEqual(recommendation_viewed["recommendation_id"], recommendations[0].recommendation_id)
        self.assertEqual(recommendation_started["action_type"], "linkedin_update")
        self.assertTrue(recommendation_completed["recalculation_requested"])

        serialized_events = repr(
            [
                recalculation_requested,
                score_recalculated,
                recommendations_generated,
                recommendation_viewed,
                recommendation_started,
                recommendation_completed,
            ]
        ).lower()
        for forbidden in (
            "resume_text",
            "linkedin_text",
            "contact_information",
            "email",
            "external_profile_url",
            "mentor_notes",
            "recruiter_notes",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, serialized_events)


if __name__ == "__main__":
    unittest.main()
