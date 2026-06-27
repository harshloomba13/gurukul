# Profile Readiness Acceptance Criteria

These scenarios define expected user-facing behavior for the first profile readiness scoring prototype. They support the root [README](../../README.md) and do not replace its product scope.

## Scenarios

### 1. Resume Import Creates An Initial Score

Given a user uploads a parseable resume, when analysis completes, then Gurukul shows a profile readiness score, readiness band, category breakdown, and at least one recommended next action.

### 2. Missing Resume Shows An Empty State

Given a user has not uploaded or imported a resume, when they open profile readiness, then Gurukul does not show a numeric score and prompts the user to upload or import a resume.

### 3. Unparseable Resume Explains The Blocker

Given a user uploads a resume that cannot be parsed, when analysis completes, then Gurukul explains that the file could not be read reliably, caps ATS compliance, withholds impact scoring, and recommends uploading a parseable file.

### 4. Missing LinkedIn Feedback Shows A Provisional Score

Given a user has a scored resume but no LinkedIn feedback, when they view readiness, then Gurukul shows a provisional score, identifies LinkedIn profile feedback as missing, and prompts the user to add or skip LinkedIn information.

### 5. Manual Profile Updates Can Change The Score

Given a user edits resume or LinkedIn feedback inputs, when readiness is recalculated, then Gurukul shows the new score, score delta, updated band when applicable, and the category that changed most.

### 6. Mentor Or Recruiter Review Adds Human Context

Given a mentor or recruiter adds review notes, when readiness is recalculated, then Gurukul includes the mentor/recruiter review category, marks the score as human-reviewed, and updates recommendations based on priority gaps from the review.

### 7. Recommendations Prioritize The Largest Gap

Given multiple categories have issues, when recommendations are generated, then Gurukul ranks the largest weighted readiness gap first and explains why that action is expected to improve readiness.

### 8. Completed Recommendations Trigger Recalculation

Given a user completes a recommended profile action, when completion is saved, then Gurukul requests a readiness recalculation and shows whether the score changed after the update.

### 9. Target Role Changes Reframe Role Alignment

Given a user changes their target role, when readiness is recalculated, then Gurukul updates role relevance inputs, preserves score history, and explains that the score changed because the target role changed.

### 10. Duplicate Imports Do Not Create False Progress

Given a user imports the same resume or LinkedIn feedback without changes, when analysis runs, then Gurukul identifies it as a duplicate import, keeps the existing score, and does not show a score increase.

### 11. Privacy-Sensitive Content Is Not Exposed In Events

Given profile readiness tracking events are emitted, when event payloads are inspected, then they contain identifiers and scoring metadata but no raw resume text, raw LinkedIn profile text, mentor/recruiter notes, contact information, or external profile URLs.

### 12. Score History Explains Changes Over Time

Given a user has multiple readiness recalculations, when they view score history, then Gurukul shows each score, band, score delta, trigger reason, and changed category without exposing private profile content.
