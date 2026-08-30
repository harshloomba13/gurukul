# Profile Readiness Signals and Events

This document defines the first-prototype tracking events for profile completion, readiness recalculation, and recommendation interactions. Events should help explain score changes and support product analytics without storing unnecessary private profile content.

## Event Principles

- Track actions and scoring metadata, not raw resume text or private LinkedIn content.
- Use stable user, profile, and score identifiers supplied by the application layer.
- Include source and confidence fields when a score or recommendation depends on inferred data.
- Emit events after the user completes an action or the system completes a recalculation.
- Keep event names scoped with the `profile_readiness_` prefix so they remain distinct from roadmap, mock interview, or salary negotiation events.

## Shared Properties

Each event should include:

| Property | Description |
| --- | --- |
| `event_id` | Unique identifier for the event. |
| `user_id` | Internal user identifier. |
| `profile_id` | Internal profile readiness record identifier. |
| `occurred_at` | Timestamp when the event occurred. |
| `source` | Action source, such as `resume_upload`, `linkedin_import`, `manual_edit`, `mentor_review`, or `system_recalculation`. |
| `schema_version` | Event schema version, starting with `1`. |

## Profile Completion Events

### `profile_readiness_resume_imported`

Emitted when a user uploads or imports a resume for readiness scoring.

Properties:

- `resume_document_id`
- `file_type`
- `parse_status`
- `detected_sections_count`
- `duplicate_import`

### `profile_readiness_linkedin_feedback_added`

Emitted when LinkedIn profile feedback is entered, imported, or updated.

Properties:

- `feedback_source`
- `completion_fields_present`
- `role_alignment_available`
- `manual_edit`

### `profile_readiness_mentor_review_added`

Emitted when mentor/recruiter review notes are added or updated.

Properties:

- `review_id`
- `reviewer_type`
- `review_score`
- `priority_gap_count`
- `review_confidence`

### `profile_readiness_completion_changed`

Emitted when required or optional profile readiness inputs move between incomplete, provisional, and complete states.

Properties:

- `previous_completion_state`
- `new_completion_state`
- `missing_required_inputs`
- `missing_optional_inputs`

## Readiness Recalculation Events

### `profile_readiness_recalculation_requested`

Emitted when a user action or system action queues a readiness recalculation.

Properties:

- `trigger_event_id`
- `trigger_reason`
- `changed_inputs`

### `profile_readiness_score_recalculated`

Emitted after the readiness score is recalculated.

Properties:

- `score_id`
- `previous_score`
- `new_score`
- `score_delta`
- `previous_band`
- `new_band`
- `category_scores`
- `category_weights`
- `provisional_score`
- `human_reviewed`
- `lowest_scoring_category`
- `calculation_version`

### `profile_readiness_score_explained`

Emitted when a user opens or views the explanation for a readiness score.

Properties:

- `score_id`
- `band`
- `highlighted_strength_count`
- `highlighted_gap_count`
- `score_history_available`

## Recommendation Interaction Events

### `profile_readiness_recommendations_generated`

Emitted when the system generates recommended profile actions after scoring.

Properties:

- `score_id`
- `recommendation_count`
- `top_category`
- `generation_reason`
- `confidence`

### `profile_readiness_recommendation_viewed`

Emitted when a user views a specific recommendation.

Properties:

- `recommendation_id`
- `score_id`
- `category`
- `rank`
- `recommendation_type`

### `profile_readiness_recommendation_started`

Emitted when a user begins acting on a recommendation.

Properties:

- `recommendation_id`
- `score_id`
- `category`
- `action_type`

### `profile_readiness_recommendation_completed`

Emitted when a user marks a recommendation complete or the system detects completion.

Properties:

- `recommendation_id`
- `score_id`
- `category`
- `completion_source`
- `recalculation_requested`

## Privacy Expectations

Events must not include raw resume text, raw LinkedIn profile text, recruiter notes, mentor notes, email addresses, phone numbers, or external profile URLs. Store references to internal document or review identifiers when later inspection is needed, and rely on application permissions before resolving those references.
