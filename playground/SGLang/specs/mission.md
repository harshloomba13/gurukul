# Mission

SGLang is a local educational repository for studying inference system design
through small, runnable Python lessons.

## Purpose

The repository explains core inference ideas with direct code, not heavy
framework abstraction. The current lessons cover:

- autoregressive LLM decoding
- KV cache behavior and speedups
- prefix caching with a radix-style lookup
- staged diffusion inference on GPU and CPU

The code should stay readable enough for a learner to trace end-to-end without
guessing where the important logic lives.

## Primary Audience

**Developers learning inference internals.** A reader should be able to open a
single lesson file and understand the concept, the execution flow, and the main
tradeoffs without needing production-serving infrastructure.

## Stakeholder Voices

- **Learner:** wants simple, inspectable code that maps closely to the concept.
- **Instructor:** wants Python modules and notebooks to stay aligned enough for
  teaching.
- **Maintainer:** wants small changes, low abstraction overhead, and local
  executability.

## What Success Looks Like

A developer reading this repository should understand:

- how causal LLM inference works token by token
- why KV cache changes complexity and throughput
- how prefix reuse can avoid repeated prefill work
- how a diffusion pipeline can be broken into explicit execution stages

The repository succeeds when those concepts are visible in the code and easy to
run locally with the expected models installed.
