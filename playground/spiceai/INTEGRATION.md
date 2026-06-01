# OpenClaw to SpiceAI Integration

## Goal

OpenClaw is the outer agent runtime.

SpiceAI is the backend for:

- SQL and query access
- retrieval and search
- OpenAI-compatible AI endpoints
- other out-of-the-box SpiceAI runtime capabilities

PostgreSQL with pgvector is infrastructure behind SpiceAI when needed. It is not the primary integration contract for OpenClaw.

## First Runtime Shape

```text
User
  ↓
OpenClaw
  ↓ HTTP
SpiceAI runtime
  ↓
Datasets / models / retrieval / Postgres-backed storage
```

## Base URL Contract

- If calling SpiceAI from the host on this machine: `http://localhost:8090`
- If OpenClaw runs in Docker and calls a host-exposed SpiceAI port: `http://host.docker.internal:8090`
- If SpiceAI runs in another reachable environment: point OpenClaw to that runtime base URL instead

Environment variables in this repo:

- `SPICE_HTTP_URL` for host-local access
- `OPENCLAW_SPICE_HTTP_URL` for OpenClaw running inside Docker
- `SPICE_MODEL=spice_assistant` for the first model target
- `SPICE_CURL_MAX_TIME=60` for helper script HTTP timeouts

## First Workflow Contract

For the first iteration, OpenClaw should:

1. accept the user turn
2. decide whether SpiceAI is needed for query, retrieval, or AI work
3. call SpiceAI rather than implementing its own storage or retrieval layer
4. return the result in OpenClaw's outer conversational flow

Grounded dataset checks should use the SQL helper or equivalent SpiceAI dataset APIs. The prompt and chat-completion helpers are direct model calls through SpiceAI and should not be treated as automatic retrieval.

## Repo-Local SpiceAI Configuration

The repo now starts with:

```yaml
datasets:
  - from: postgres:public.project_context
  - from: postgres:public.integration_targets
models:
  - from: huggingface:huggingface.co/itlwas/TinyLlama-1.1B-Chat-v1.0-Q4_K_M-GGUF
    name: spice_assistant
```

This configuration exists to prove that:

- SpiceAI starts correctly
- the runtime is reachable from OpenClaw
- PostgreSQL-backed datasets can be queried through SpiceAI
- OpenClaw can call SpiceAI's model APIs against a local free model target

## OpenClaw Call Surface

The workspace includes direct helpers for the first integration:

- `openclaw-workspace/scripts/spice_ready.sh`
- `openclaw-workspace/scripts/spice_sql.sh`
- `openclaw-workspace/scripts/spice_chat_completions.sh`

Example usage:

```bash
./openclaw-workspace/scripts/spice_ready.sh
./openclaw-workspace/scripts/spice_sql.sh < openclaw-workspace/examples/sql/project_context.sql
./openclaw-workspace/scripts/spice_chat_completions.sh < openclaw-workspace/examples/json/chat-completion.json
```

## What Not To Build Yet

- a custom agent memory schema
- a parallel retrieval service outside SpiceAI
- Slack-specific runtime logic in the core OpenClaw-to-SpiceAI path
