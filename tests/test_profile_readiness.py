from __future__ import annotations

import unittest
from datetime import datetime, timezone

from profile_readiness import (
    ProfileReadinessInput,
    build_recalculation_requested_event,
    build_recommendation_completed_event,
    build_recommendation_started_event,
    build_recommendation_viewed_event,
    build_recommendations_generated_event,
    build_score_recalculated_event,
    calculate_readiness,
    generate_recommendations,
    readiness_band_for_score,
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
