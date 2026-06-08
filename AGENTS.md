# AGENTS.md

## Repo Purpose
- `gurukul` is a product-planning repository for an interview-prep platform.
- The root `README.md` currently captures functional requirements and feature areas.

## Working Agreement
- Keep changes small, explicit, and easy to review.
- Prefer updating existing files over introducing new abstractions.
- Preserve the current product terminology used in `README.md`.
- When requirements are unclear, infer the smallest sensible change and call out assumptions.

## Repo Conventions
- Treat the root `README.md` as the current source of truth for product scope unless the user says otherwise.
- If you add implementation files, group them by feature area and keep names descriptive.
- Avoid rewriting large requirement sections unless the task explicitly asks for it.

## Validation
- For documentation-only changes, verify formatting and internal consistency.
- For code changes, run the narrowest relevant checks first and summarize anything you could not validate.

## Notes For Future Agents
- Start by checking for more specific `AGENTS.md` files in subdirectories before editing there.
- If the repo grows into multiple apps or services, add scoped `AGENTS.md` files near each project.
