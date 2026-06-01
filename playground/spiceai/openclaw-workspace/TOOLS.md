# SpiceAI Tooling Notes

The first implementation phase should expect these capabilities:

- call SpiceAI over HTTP for governed data access
- use SpiceAI retrieval and search capabilities
- rely on SpiceAI instead of a parallel custom persistence layer where possible
- call the local helper scripts in `openclaw-workspace/scripts/` for readiness checks, SQL, and chat completions
- use `scripts/spice_prompt.sh` when OpenClaw needs a direct model call through SpiceAI

When OpenClaw runs in Docker and SpiceAI runs on the host, prefer `http://host.docker.internal:8090`.

Workspace scripts:

- `scripts/spice_ready.sh`
- `scripts/spice_prompt.sh`
- `scripts/spice_sql.sh`
- `scripts/spice_chat_completions.sh`

The Slack transport is intentionally out of scope for this phase.

Set `SPICE_CURL_MAX_TIME` to control the helper script timeout in seconds. The default is `60`.
