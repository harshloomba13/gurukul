# Tech Stack

## Language & Runtime

- **Python 3.12** — local runtime for lessons and notebooks
- **Jupyter notebooks** — parallel lesson format for interactive study

## Core ML Libraries

- **PyTorch** — tensor runtime and inference execution
- **Transformers** — causal language model loading, tokenization, and generation
- **Diffusers** — diffusion pipeline components and schedulers
- **Accelerate** — model loading support for device placement and memory-aware execution

## Data / Analysis

- **NumPy** — array utilities for lesson analysis
- **Pandas** — tabular experiment summaries
- **Matplotlib** — plots and visual comparisons
- **tqdm** — progress bars for iterative diffusion steps

## Current Code Organization

- Root-level Python lesson modules:
  - `L2.py` — LLM inference fundamentals
  - `L3.py` — prefix caching / radix-style reuse
  - `L4.py` — GPU-oriented diffusion pipeline
  - `L4_cpu.py` — CPU-oriented diffusion pipeline
- Shared helpers:
  - `helper.py`
  - `tiny_llm.py`
  - `caching.py` (currently empty placeholder)
- Notebook variants:
  - `L3 (1).ipynb`
  - `L4 (1).ipynb`
  - `L4_cpu.ipynb`

## Model Dependencies

- **DeepSeek / Qwen-style causal LM checkpoints** for LLM lessons
- **`Tongyi-MAI/Z-Image-Turbo`** for diffusion lessons
- Some lesson defaults also assume local model directories such as `../models/...`

## Architectural Style

- **Lesson-first modules** — each file keeps enough code inline to teach one concept
- **Local, in-memory execution** — no service layer, database, or persistent cache
- **Stage-based diffusion pipeline** — explicit pipeline stages instead of a hidden monolith
- **Wrapper-based LLM access** — `TinyLLM` centralizes common model operations

## Constraints

- Readability is preferred over aggressive abstraction.
- Notebook and Python behavior should not drift unnecessarily.
- The repository is not currently structured as a reusable package.
- Hardware and local model availability are assumed.

## Gaps / Future Considerations

- `requirements.txt` appears incomplete relative to imports in the repo.
- There are two `TinyLLM` implementations, which may drift.
- Cache logic is still lesson-local rather than centralized.
- No automated test or smoke-check workflow is defined yet.
