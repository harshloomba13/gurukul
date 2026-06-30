---
name: vocal-bridge-escalation
description: Call the human through Vocal Bridge only when coding work is blocked on a genuine human decision.
---

# Vocal Bridge Escalation

Use this skill when autonomous coding work is blocked and a human decision is required before it is safe or useful to continue. The loop is:

blocked -> call -> decide -> resume

The goal is not to call often. The goal is to avoid losing agent time when one human decision is the only blocker.

## Local Setup

This repo includes a Vocal Bridge client at `playground/minions`. Use it to confirm the agent and token route are configured. The local browser client at `http://127.0.0.1:3000/` is useful for testing the connected agent, but outbound phone escalation should use the `vb` CLI.

Required runtime setup:

- `VOCAL_BRIDGE_API_KEY` is configured in `playground/minions/.env.local` or the shell environment.
- `VOCAL_BRIDGE_AGENT_ID` is configured when the key is account-level.
- `VOCAL_BRIDGE_ESCALATION_PHONE` is set to the phone number to call.
- The `vb` CLI is installed and authenticated, or can read `VOCAL_BRIDGE_API_KEY`.

Never print, commit, or speak API keys, tokens, secrets, private file contents, or credential values.

## Minions Runbook

Use this runbook when the work is running through the local file-ticket minion workflow. Commands assume the repo root unless they start with `cd playground/minions`.

```bash
cd playground/minions

# Inspect the local Jira-like queue.
python3 quarter.py list

# Reset all current ticket files, or reset one ticket.
python3 quarter.py reset
python3 quarter.py reset --ticket GURU-106

# Preview or run a one-pass assigned-ticket workflow.
python3 quarter.py plan --runner codex-ollama --draft-pr
OLLAMA_MODEL=qwen2.5-coder:7b python3 quarter.py watch --assigned-to minion --once --runner codex-ollama --draft-pr --stop-on-failure

# Keep listening for newly assigned tickets.
OLLAMA_MODEL=qwen2.5-coder:7b python3 quarter.py watch --assigned-to minion --runner codex-ollama --draft-pr --stop-on-failure

# Record a clear human answer if transcript parsing could not resume automatically.
python3 quarter.py answer --ticket GURU-106 --answer session
```

Operational rules:

- Assign work by editing a ticket's `Assignee:` field to `minion` or the watcher identity passed with `--assigned-to`.
- Prefer `--runner codex-ollama` with `OLLAMA_MODEL=qwen2.5-coder:7b` when the user wants local LLM execution instead of hosted Cursor/Codex calls. Check `ollama list` first; pull a missing model only when the user requested or approved it.
- Finished tickets are recorded under `playground/minions/.runs/quarter/state.json`. Tickets marked `done` or `blocked` are skipped by the watcher until reset or explicitly included.
- In `--draft-pr` mode, the inner coding agent must not branch, commit, push, open PRs, or run `gh auth login`. It should write the publish manifest; the outer launcher owns GitHub publishing with the user's terminal auth.
- If GitHub auth, production deploys, broad destructive cleanup, or another human-only permission blocks delivery, use this voice escalation skill before proceeding.
- For a call-path smoke test, use `tickets/JiraCallTest.txt` with `RequiresHumanInput: true` and `CallOnly: true`; it should call without editing product files.
- After surprising behavior, capture feedback and generate a reviewable improvement report:

```bash
python3 quarter.py feedback --ticket GURU-101 --rating bad --category voice --note "The call did not ask the real blocker."
python3 quarter.py improve --ticket GURU-101 --last 5
```

Review improvement reports before editing `SKILL.md`, `minion.py`, or `quarter.py`; the loop should propose changes, not silently rewrite workflow code.

## Call Gate

Before calling, try to resolve the issue from repo instructions, code context, tests, and reversible local choices. Call only when the next action requires user judgment, authorization, or user-only information.

Call for:

- Destructive or hard-to-reverse actions: deleting data, force-pushing, rewriting published history, dropping migrations, overwriting user work, or running broad cleanup commands.
- External side effects: production deploys, billing changes, public releases, sending emails/messages, changing live Vocal Bridge agent config, or modifying third-party services.
- Security or privacy risk: exposing credentials, changing auth behavior, handling private data, or loosening safeguards.
- Human-only account or permission steps that block requested delivery: expired GitHub CLI auth, login prompts, missing permission to create a branch/PR, or a publish step that needs the user to approve or perform an authenticated action.
- Product or architecture tradeoffs where the correct choice depends on user preference: latency versus safety, scope versus schedule, quality versus cost, compatibility versus cleanup.
- Scope changes: a subagent, tool, or dependency proposes work outside the original task.
- Missing user-only information: phone number, account choice, API key location, business policy, or acceptance criteria that cannot be inferred.

Do not call for:

- Routine build, lint, typecheck, or test failures the agent can investigate.
- Local implementation choices with a clear safest option.
- Small documentation wording choices.
- Recoverable tool or network errors unless the next step requires user approval.
- Decisions already answered by `AGENTS.md`, README, issue text, or prior user messages.

If the situation is important but not blocking, continue with the safest reversible path and mention the assumption in the final response.

## Spoken Brief

Prepare the message like a short voicemail to a busy colleague. Keep it under about 45 seconds.

Use this structure:

```text
I'm blocked on <task>.
Stakes: <what can go wrong or what delay this causes>.
Recommended option: <option and why>.
Alternative: <option and tradeoff>.
Please answer with <exact words/options>.
If I do not get a clear answer, I will <safe fallback>.
```

Good briefs are concrete:

- Name the repo, feature, or command only as much as needed.
- Offer two or three options, not an open-ended discussion.
- State the recommended option first when there is one.
- Include the fail-safe behavior.
- Avoid code dumps, stack traces, secrets, and long file paths unless essential.

## Execution

1. Write the brief to a temp file outside the repo, for example `/tmp/vb-escalation.txt`.
2. From the repo root, run:

   ```bash
   python3 playground/minions/vocal.py --message-file /tmp/vb-escalation.txt
   ```

3. If the current Vocal Bridge agent is not already configured to speak escalation briefs, either:
   - update the agent prompt manually through the Vocal Bridge dashboard or `vb prompt`, or
   - run the helper with `--set-agent-prompt` only after recognizing that this changes live agent configuration.
4. After the call, inspect the latest call transcript:

   ```bash
   python3 playground/minions/vocal.py --logs
   python3 playground/minions/vocal.py --show-session <session_id>
   ```

5. Resume only on a clear answer.

The helper prints the escalation brief locally and invokes `vb call <phone>`. It does not treat the call as approval by itself; the transcript or clear user answer is the approval source.

The Vocal Bridge dashboard greeting is static. Keep it generic, such as "I am calling with a specific blocker and will read the decision brief now." Do not put a specific ticket or stale problem in the dashboard greeting. The actual blocker is supplied by `playground/minions/vocal.py`, which sets the live agent prompt from the brief before each call unless explicitly disabled.

When this skill is used through `playground/minions/minion.py`, follow the launcher's prompt if it says the outer launcher owns the call. In that mode, write the brief to the provided `/tmp/vb-escalation-...txt` path and stop with `MINION_BLOCKED: <path>`. The outer minion launcher will place the phone call from outside the coding-agent sandbox and return a blocked status.

## Response Handling

- Clear approval: perform only the approved action and record the decision in the final response.
- Clear option choice: follow that option and keep the implementation within the chosen scope.
- Clear denial: do not perform the action; choose the safest alternative if one was authorized, otherwise stop.
- Ambiguous answer: do not perform destructive or external actions. Continue only with reversible local work.
- No answer, failed call, missing phone, missing auth, or missing `vb`: stop at the blocked point and leave the exact decision needed.

## Examples

| Scenario | Call? | Reason |
| --- | --- | --- |
| `rm -rf` is needed to remove generated artifacts but the path may contain user work. | Yes | Destructive filesystem action needs explicit approval. |
| TypeScript fails because a prop name changed. | No | The agent can inspect and fix this locally. |
| Two fixes exist: distributed lock adds latency; sequential processing reduces throughput. | Yes | The right tradeoff depends on product tolerance. |
| A package install fails because the network is blocked. | No | Ask for normal tool escalation or use an existing dependency; do not phone by default. |
| Deployment to production is ready. | Yes | External irreversible side effect. |
| Draft PR is requested but `gh auth status` reports an invalid token. | Yes | Refreshing auth is a human-only account action required to finish delivery. |

## Message Template

```text
I'm blocked on the Gurukul coding task.
Stakes: I can keep working only after choosing between two safe but different paths.
Recommended option: <A>. It <benefit> but <tradeoff>.
Alternative: <B>. It <benefit> but <tradeoff>.
Please answer "A", "B", or "stop".
If I do not get a clear answer, I will stop before making the risky change.
```
