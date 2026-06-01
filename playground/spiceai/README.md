# SpiceAI

SpiceAI is the project focus in this repo. OpenClaw is the agent runtime, SpiceAI is the data and AI layer, and PostgreSQL with pgvector is supporting infrastructure for SpiceAI where needed.

Phase 1 focuses on a local-first foundation with production-minded isolation:

- OpenClaw runs the agent runtime, preferably in Docker for isolation.
- SpiceAI provides the query, retrieval, and AI runtime.
- PostgreSQL with pgvector supports SpiceAI storage and vector workloads when configured.
- The initial workflow uses repo-local SpiceAI datasets backed by PostgreSQL plus a quantized public Hugging Face GGUF model named `spice_assistant`.
- On this Intel macOS setup, SpiceAI should run in Docker because the native CLI binaries are not supported for `darwin-x86_64`.
- The assistant exposes a single product identity: `SpiceAI`.

Phase 2 adds Slack as a communication layer on top of the same core agent.

## Product Scope

SpiceAI should provide:

- a governed AI runtime built around SpiceAI
- an isolated OpenClaw agent runtime in Docker
- access to SpiceAI out-of-the-box capabilities
- PostgreSQL with pgvector as optional supporting infrastructure
- a clean path to adding Slack later as a communication layer

The assistant should remain channel-agnostic. Slack is a delivery layer, not the core product.

## Deployment Stance

OpenClaw's official docs describe Docker as optional for a containerized gateway, not mandatory for the fastest local dev loop. For SpiceAI, the recommended default is stricter:

- run OpenClaw in Docker
- run SpiceAI in Docker on this machine
- keep PostgreSQL with pgvector available for SpiceAI instead of building a parallel app data layer

Why this repo prefers Docker for OpenClaw:

- OpenClaw can access files, execute commands, call APIs, and persist memory.
- Once OpenClaw is connected to SpiceAI, the agent has meaningful access to real data.
- Container isolation reduces filesystem exposure, credential sprawl, and recovery complexity.

Use a fully local setup only for short-lived prototyping with mock data and non-sensitive credentials.

## Architecture

Current target architecture:

1. OpenClaw provides the agent runtime and tool loop.
2. SpiceAI provides governed query access, retrieval, and AI endpoints.
3. PostgreSQL with pgvector supports SpiceAI storage and vector primitives where required.
4. A future Slack adapter will translate Slack events into SpiceAI messages and route responses back to Slack.

Recommended topology:

```text
[Docker] OpenClaw
        ↓
[Docker] SpiceAI
        ↓
[Postgres + pgvector + local DBs + APIs + files]
```

For local validation from the host, use `http://localhost:8090`.
For OpenClaw running in Docker and calling a host-exposed SpiceAI port, use `http://host.docker.internal:8090`.

## Repo Layout

- `docker-compose.yml`: local PostgreSQL + pgvector plus SpiceAI runtime bootstrap
- `.env.example`: environment variables expected by the local setup
- `spicepod.yaml`: SpiceAI datasets and model definition for this repo
- `openclaw.json.example`: OpenClaw config template pointing at this workspace
- `INTEGRATION.md`: OpenClaw-to-SpiceAI integration contract
- `openclaw-workspace/`: initial OpenClaw workspace files for SpiceAI

## Local Setup

1. Copy env vars:

   ```bash
   cp .env.example .env
   ```

2. Start PostgreSQL with pgvector and SpiceAI:

   ```bash
   docker compose up -d postgres spiceai
   ```

3. The included `spicepod.yaml` defines:

   - PostgreSQL-backed datasets: `project_context` and `integration_targets`
   - a Hugging Face GGUF-backed model: `spice_assistant`

4. Install and configure OpenClaw separately.

5. Point OpenClaw at `openclaw-workspace/` as the workspace for this project.

6. For host-side checks, the helper scripts target `SPICE_HTTP_URL=http://localhost:8090`.

7. If OpenClaw runs in Docker and SpiceAI is exposed on the host, target `http://host.docker.internal:8090` for SpiceAI HTTP access.

8. Use the workspace helper scripts for the first integration pass:

   ```bash
   ./openclaw-workspace/scripts/spice_ready.sh
   ./openclaw-workspace/scripts/spice_prompt.sh "What should OpenClaw call when running in Docker?"
   ./openclaw-workspace/scripts/spice_sql.sh < openclaw-workspace/examples/sql/project_context.sql
   ./openclaw-workspace/scripts/spice_chat_completions.sh < openclaw-workspace/examples/json/chat-completion.json
   ```

9. Point OpenClaw at [openclaw.json.example](/Users/harshloomba/Documents/gurukul/playground/spiceai/openclaw.json.example) as the base config shape, or copy its contents into `~/.openclaw/openclaw.json`.

## First Workflow

The first workflow is intentionally simple:

1. OpenClaw receives a user request.
2. OpenClaw calls SpiceAI over HTTP.
3. SpiceAI handles query, search, retrieval, or model-facing behavior using its built-in capabilities.
4. OpenClaw formats the result for the user and remains the outer agent runtime.

This repo does not add a parallel memory or retrieval implementation ahead of SpiceAI. The first goal is proving the integration path with SpiceAI's configured datasets, model, and APIs.

## First Datasets And Model

`spicepod.yaml` defines:

- `project_context`: PostgreSQL-backed repo context records
- `integration_targets`: PostgreSQL-backed endpoint and routing records
- `spice_assistant`: a quantized TinyLlama 1.1B Chat GGUF model served by SpiceAI

The Postgres seed lives in `db/init/001_spiceai_bootstrap.sql` and is loaded automatically on first container initialization.
The PostgreSQL datasets explicitly use `pg_sslmode: disable` because the default local Docker setup is not serving TLS.

## Security Rules

- Treat Docker isolation for OpenClaw as the default, not an optional hardening step.
- Do not mount broad host directories into the OpenClaw container.
- Do not expose OpenClaw over LAN without explicit auth and network controls.
- Keep real credentials out of the repo and scope runtime env vars narrowly.

## Assumptions

- The shared ChatGPT link was not readable from this environment, so this scaffold is based on the request text alone.
- `SpiceAI` is the product focus for this repo.
- OpenClaw and SpiceAI will be run as external dependencies instead of being vendored into this repo.
- The first implementation step is defining the integration boundary before adding custom tools or schema.

## Next Steps

- connect the OpenClaw runtime to the helper scripts or equivalent HTTP tools
- replace the seed datasets with the first production data sources
- add Slack event ingestion and response delivery
