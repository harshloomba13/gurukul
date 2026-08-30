# Profile Readiness Documentation

This documentation pack supports the Profile & Application Readiness area of Gurukul's product scope. The root [README](../../README.md) remains the source of truth for the overall product; these docs define the first-prototype behavior for calculating, explaining, and tracking profile readiness before prep begins.

## User Problem

Candidates often enter interview prep with uneven resume quality, incomplete LinkedIn information, unclear evidence of impact, or no recruiter/mentor review. Gurukul should help users understand how ready their profile is, which gaps matter most, and what actions can improve their readiness score before they spend time on roadmap tasks, mock exams, or salary negotiation support.

## First Prototype Scope

The first prototype should:

- calculate a profile readiness score from resume ATS compliance, formatting, impact, LinkedIn profile feedback, and optional mentor/recruiter review notes;
- show the score as a readiness band with a short explanation of the strongest and weakest categories;
- track score changes after profile imports, manual edits, feedback updates, or mentor/recruiter review notes;
- recommend the next best profile actions based on the largest weighted readiness gaps;
- preserve enough scoring context to explain why the score changed;
- keep analytics events focused on scoring metadata instead of raw resume, LinkedIn, or review content.

## Out Of Scope

The first prototype should not:

- guarantee job application outcomes or interview callbacks;
- replace human mentor/recruiter judgment;
- automatically submit resumes, LinkedIn updates, or job applications;
- scrape private LinkedIn data without explicit user action;
- compare users against named peers or expose another user's profile signals;
- calculate interview readiness scoring, which remains part of Mock Exams & Interviews;
- expand or replace the product scope defined in the root README.

## Supporting Docs

- [Scoring model](scoring-model.md) defines categories, inputs, weights, readiness bands, and edge cases.
- [Signals and events](signals-and-events.md) defines the tracking events needed for imports, recalculation, and recommendation interactions.
- [Acceptance criteria](acceptance-criteria.md) defines user-facing scenarios for prototype acceptance.
