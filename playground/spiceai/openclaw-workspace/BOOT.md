# Boot Checklist

On startup:

1. Run `./scripts/spice_ready.sh`.
2. If SpiceAI is not ready, tell the user the backend is unavailable before attempting model calls.
3. Prefer `./scripts/spice_prompt.sh "..."` for normal prompt-style calls into SpiceAI.
4. Use `./scripts/spice_sql.sh` for direct dataset queries when the task is clearly SQL-shaped.
