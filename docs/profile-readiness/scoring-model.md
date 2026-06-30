# Profile Readiness Scoring Model

This model defines how the first prototype calculates the profile readiness score named in the root [README](../../README.md). The score summarizes resume and LinkedIn profile strength before prep and highlights priority gaps for users to address.

## Score Categories

| Category | Weight | Purpose |
| --- | ---: | --- |
| Resume ATS compliance | 30% | Measures whether the resume can be parsed and screened by applicant tracking systems. |
| Resume formatting | 15% | Measures readability, structure, section clarity, length, and consistency. |
| Resume impact | 25% | Measures outcome-oriented bullets, quantified achievements, role relevance, and clarity of scope. |
| LinkedIn profile feedback | 20% | Measures completeness and alignment between LinkedIn profile, target role, and resume narrative. |
| Mentor/recruiter review | 10% | Incorporates optional qualitative feedback from a mentor or recruiter. |

Weights must sum to 100%. Category scores use a 0 to 100 scale before weighting.

## Inputs

The scoring model accepts these inputs:

- uploaded resume text and parser metadata;
- ATS compliance findings, including parse success, contact information presence, section detection, keyword alignment, and unsupported formatting flags;
- formatting findings, including section order, bullet consistency, page length, tense consistency, and readability issues;
- impact findings, including quantified outcomes, action verbs, role relevance, seniority signals, and repeated vague claims;
- LinkedIn profile feedback entered or imported by the user, including headline, About section, experience completeness, skills, projects, and consistency with the resume;
- optional mentor/recruiter review notes, including a rating, priority gaps, and confidence level when provided.

If a target role is available from roadmap creation, role relevance should use that target role. If no target role is available, the category should use general interview-prep quality checks and clearly mark role-specific guidance as limited.

## Weighted Calculation

Calculate the overall readiness score with this formula:

```text
overall_score =
  (ats_score * 0.30) +
  (formatting_score * 0.15) +
  (impact_score * 0.25) +
  (linkedin_score * 0.20) +
  (mentor_review_score * 0.10)
```

Round the final score to the nearest whole number. Store the unrounded value for change tracking so small improvements are not lost across recalculations.

## Readiness Bands

| Band | Score Range | User Meaning |
| --- | ---: | --- |
| Not ready | 0-39 | Major profile gaps block effective application prep. |
| Needs work | 40-64 | Core profile exists, but important gaps remain. |
| Approaching ready | 65-79 | Profile is usable, with focused improvements recommended. |
| Ready | 80-89 | Profile is strong enough to support active prep and applications. |
| Strong | 90-100 | Profile is polished, consistent, and role-aligned. |

The interface should display both the numeric score and the readiness band. Recommendations should prioritize the largest weighted readiness gap, calculated as `(100 - category_score) * category_weight`, then the highest-impact unresolved issue within that category.

## Edge Cases

- No resume uploaded: return no overall score, show an empty state, and prompt the user to import or upload a resume.
- Resume cannot be parsed: cap ATS compliance at 20, withhold impact scoring until readable text is available, and recommend uploading a parseable file.
- Missing LinkedIn data: set LinkedIn profile feedback to 0 only after the user skips or confirms they do not want to provide it; otherwise mark it incomplete and show a provisional score.
- No mentor/recruiter review: use a neutral default of 50 for the mentor/recruiter review category and label the score as not yet human-reviewed.
- Conflicting mentor/recruiter review notes: use the most recent review as the active score input and preserve prior reviews in score history.
- Target role changes: recalculate role relevance inputs and create a score history entry explaining that the target role changed.
- Duplicate imports: ignore exact duplicate resume or LinkedIn imports and do not create a new score-change event.
- Low confidence findings: include the score, but show that recommendations are based on limited evidence.
