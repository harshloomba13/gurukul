# Gurukul Voice Agent

Minimal Next.js voice interface for the Gurukul agent using Vocal Bridge.

## Run

```bash
npm install
npm run dev
```

The app reads `VOCAL_BRIDGE_API_KEY` from `.env.local`. Keep the API key server-side; the browser only calls `/api/voice-token`.

If the key is account-level, also set `VOCAL_BRIDGE_AGENT_ID` to the agent UUID. The token route automatically forwards it as `X-Agent-Id`.

## Coding-Agent Escalation Calls

This client can be used as the local Vocal Bridge setup for the `vocal-bridge-escalation` skill in `../skills/vocal-bridge-escalation/SKILL.md`.

Add the phone number to call to `.env.local` or your shell:

```bash
VOCAL_BRIDGE_ESCALATION_PHONE=+15551234567
```

To use the browser voice session instead of an outbound phone call, set:

```bash
VOCAL_BRIDGE_ESCALATION_TRANSPORT=browser
VOCAL_BRIDGE_BROWSER_URL=http://localhost:3000/?autostart=1
```

Prepare a short decision brief outside the repo, then place the call:

```bash
python3 vocal.py --message-file /tmp/vb-escalation.txt
```

The helper loads `.env.local`, sets the live Vocal Bridge agent prompt from the brief, verifies the `vb` CLI is available, and then either runs `vb call <phone>` or opens the browser session URL. It prints the brief locally so the coding agent can verify what it is escalating.

In the Vocal Bridge dashboard, keep the outbound greeting generic because it is static. For example:

```text
Hi, this is your coding minion. I am calling with a specific blocker and will read the decision brief now.
```

Do not put a specific ticket, feature, or old blocker in the dashboard greeting or system prompt. The specific problem comes from `vocal.py`, which updates the live prompt before each call. To skip that live prompt update for manual experiments, pass `--no-set-agent-prompt`.

After the call, inspect the transcript:

```bash
python3 vocal.py --logs
python3 vocal.py --show-session <session_id>
```

## One-Shot Coding Minions

Use `minion.py` when you want a Stripe-Minions-style terminal workflow: give a coding agent a complex task, let it plan and execute, and have it call you only if it reaches a human-only decision.

Preview the generated agent prompt without launching anything:

```bash
python3 minion.py "Create a Trie-based autocomplete prototype for Gurukul search" --dry-run
```

Run with Codex, the default runner:

```bash
python3 minion.py "Create a Trie-based autocomplete prototype for Gurukul search"
```

Run with Codex backed by local Ollama instead of a hosted coding model:

```bash
OLLAMA_MODEL=qwen2.5:0.5b python3 minion.py "Create a Trie-based autocomplete prototype for Gurukul search" --runner codex-ollama
```

Make sure Ollama is running first:

```bash
ollama serve
ollama ps
```

Run with Cursor Agent in an isolated worktree:

```bash
python3 minion.py "Create a Trie-based autocomplete prototype for Gurukul search" --runner cursor --worktree
```

The launcher injects the Vocal Bridge escalation skill into the agent prompt. The agent should continue autonomously for ordinary implementation work. When a call is warranted, the coding agent writes a brief and stops; the outer launcher places the call from outside the sandbox and the ticket is marked `blocked` until it is reset or explicitly included again.

In draft PR mode, the inner coding agent does not create branches, commit, push, or call `gh`. It writes a publish manifest listing the exact files, commit message, PR title, and PR body. The outer launcher then stages only those files, creates the ticket branch, commits, pushes, and opens the draft PR using the user's normal terminal GitHub auth.

## Quarter Ticket Runs

For a local Jira-like workflow, put tickets in `tickets/*.txt`. Each file should include at least a `Key:`, `Title:`, and acceptance criteria. The sample files `Jira1.txt`, `Jira2.txt`, and `Jira3.txt` show the intended format.

List the queue:

```bash
python3 quarter.py list
```

Preview assignments without launching minions:

```bash
python3 quarter.py plan --runner cursor --worktree --draft-pr
```

Run the queue:

```bash
python3 quarter.py run --runner cursor --worktree --draft-pr --stop-on-failure
```

The quarter runner assigns each ticket file to `minion.py`, writes logs under `.runs/quarter/`, and records status in `.runs/quarter/state.json`. Parallel runs now use temporary git worktrees so separate PRs can be built at the same time without colliding in one checkout. Pass `--sequential` if you want the old one-at-a-time behavior. Each minion gets the voice escalation instructions and should call only when blocked on human input. Tickets can end as `done`, `failed`, or `blocked`; blocked tickets are skipped by the watcher until you reset them or pass `--include-blocked`.

`quarter.py run` and `quarter.py watch` now also open the local observer page at `/observer` so you can watch ticket state and log tails live while the run is active.

Before and after each `run` or watcher batch, `quarter.py` cleans up stale minions-owned runner processes that can leave the next run or observer in a bad local state. The cleanup is scoped to this minions workspace and covers stale `minion.py`, `codex exec`, `cursor-agent`, and `next build` processes; it leaves the observer dev server running. Pass `--skip-process-cleanup` if you are intentionally running one of those processes in another terminal.

When a ticket is blocked by a voice escalation, `minion.py` asks `vocal.py` to wait for a clear transcript answer when the brief contains exact allowed options. On a clear answer, the launcher reruns the same minion with the answer injected into the prompt, so it resumes without calling again for the same decision.

If automatic transcript parsing cannot find a clear answer, use the manual fallback: record the exact answer from the call and rerun the ticket.

```bash
python3 quarter.py answer --ticket GURU-106 --answer session
python3 quarter.py watch --ticket GURU-106 --once --runner codex --draft-pr --stop-on-failure
```

Use the exact option from the call, such as `session`, `json`, `sqlite`, or `stop`. If a continuous watcher is still running, recording the answer marks the ticket pending so the watcher can pick it up on its next poll.

`quarter.py reset` now defaults to the current ticket files under `tickets/`. Use `--ticket` to reset one or more specific entries.

## Auto-Run Assigned Tickets

Tickets can auto-run when assigned by adding an `Assignee:` line:

```text
Key: GURU-104
Title: Build roadmap export
Priority: Medium
Assignee: minion
```

Run one pass over tickets assigned to `minion`:

```bash
python3 quarter.py watch --assigned-to minion --once --runner print
```

Continuously watch and launch real minions for assigned tickets:

```bash
python3 quarter.py watch --assigned-to minion --runner cursor --worktree --draft-pr --stop-on-failure
```

To avoid Cursor API calls, use the local Ollama runner:

```bash
OLLAMA_MODEL=qwen2.5:0.5b python3 quarter.py watch --assigned-to minion --runner codex-ollama --draft-pr --stop-on-failure
```

To assign a ticket, edit its `Assignee:` from `unassigned` to `minion` or a specific identity such as `minion-1`, then run the watcher with the matching `--assigned-to` value. Finished tickets are recorded in `.runs/quarter/state.json` and will not run again when they are `done` or `blocked` unless you reset them:

```bash
python3 quarter.py reset --ticket GURU-104
```

## Voice Call Smoke Test

Use `tickets/JiraCallTest.txt` to prove assigned tickets can call you without waiting for the local LLM.

1. Edit the ticket:

   ```text
   Assignee: minion
   ```

2. Run the watcher:

   ```bash
   python3 quarter.py watch --assigned-to minion --once --runner print
   ```

The ticket has `RequiresHumanInput: true` and `CallOnly: true`, so the quarter runner writes a voice brief, invokes `vocal.py`, and stops after the call-path validation. It does not edit product files.

## Live Quarter Observer

The observer page shows the current quarter run, status counts, and live log tails for tickets in flight:

```bash
python3 quarter.py run --runner cursor --worktree --draft-pr --stop-on-failure
```

The launcher opens `http://localhost:3000/observer?run=<run_id>&autostart=1` automatically when it starts a run. If the browser does not open, open the URL manually after the Next.js app is running.

## Self-Improvement Loop

The inner loop is the ticket runner: `quarter.py watch` assigns work to `minion.py`, writes logs, and records ticket state.

The outer loop is a review pass over recent runs and human feedback. Record feedback when a run surprises you:

```bash
python3 quarter.py feedback \
  --ticket GURU-101 \
  --rating bad \
  --category status \
  --note "The ticket was marked done even though the draft PR was blocked."
```

Generate a reviewable improvement report:

```bash
python3 quarter.py improve --ticket GURU-101 --last 5
```

Reports are written under `.runs/quarter/improvements/`. They summarize feedback, recent run signals, and recommended changes. The loop does not auto-edit Skills or workflow code; use the report to make a reviewed patch.
