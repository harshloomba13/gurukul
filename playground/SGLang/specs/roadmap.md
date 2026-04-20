# Roadmap

## Phase 1: Repository Constitution

Define the repository as a lesson-oriented inference study project with a small
spec set instead of a single ad hoc design doc.

Status: complete

## Phase 2: Documentation Baseline

Establish the core repo docs needed to guide future work:

- `specs/mission.md`
- `specs/tech-stack.md`
- `specs/roadmap.md`

Status: complete

## Phase 3: Documentation Hygiene

Close the main documentation gaps visible in the current checkout.

### Candidate work

- Add a root `README.md` describing lessons, setup, and expected model paths.
- Document how notebooks relate to the Python lesson modules.
- Clarify whether `tiny_llm.py` or `helper.py` owns the canonical `TinyLLM`.

Status: next

## Phase 4: Environment Reliability

Make the repo easier to run consistently on a fresh local machine.

### Candidate work

- Align `requirements.txt` with actual imports used by the lessons.
- Add a minimal smoke-check flow for imports and module entry points.
- Document CPU vs GPU expectations and memory constraints.

Status: planned

## Phase 5: Structural Cleanup

Reduce drift and duplicated concepts while preserving the teaching value of the
lessons.

### Candidate work

- Decide whether cache abstractions should move into `caching.py`.
- Reduce duplication between helper utilities and lesson-local implementations.
- Introduce clearer grouping if the repo grows beyond a handful of lesson files.

Status: planned

## Phase 6: Feature Specs

When new work is requested, add dated spec folders under `specs/` using the
same convention as the reference repo:

- `specs/YYYY-MM-DD-feature-name/requirements.md`
- `specs/YYYY-MM-DD-feature-name/plan.md`
- `specs/YYYY-MM-DD-feature-name/validation.md`

Suggested first candidates:

- root README and local setup guide
- dependency and environment cleanup
- unified cache abstraction extraction

Status: ready when implementation work starts
