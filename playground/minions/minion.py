#!/usr/bin/env python3
"""Launch one-shot coding minions with Vocal Bridge escalation instructions."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


MINIONS_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(os.environ.get("MINION_REPO_ROOT", MINIONS_DIR.parents[1])).resolve()
SKILL_PATH = REPO_ROOT / "playground" / "skills" / "vocal-bridge-escalation" / "SKILL.md"
RUNS_DIR = MINIONS_DIR / ".runs"
BLOCKED_EXIT_CODE = 20


def read_task(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if args.task:
        parts.append(" ".join(args.task).strip())
    if args.task_file:
        parts.append(Path(args.task_file).read_text(encoding="utf-8").strip())
    if not parts and not sys.stdin.isatty():
        parts.append(sys.stdin.read().strip())
    if args.human_decision:
        decision = args.human_decision.strip()
        note = args.human_decision_note.strip()
        decision_lines = [
            "## Human Decision From Prior Voice Call",
            "",
            f"The human answered: `{decision}`.",
            "",
            "Use this exact answer to resume the blocker already escalated by voice.",
            "Do not call again for the same decision.",
            "If the answer is not valid for this ticket's allowed options, stop before changing product code and report the blocker.",
        ]
        if note:
            decision_lines.extend(["", f"Decision note: {note}"])
        parts.append("\n".join(decision_lines))

    task = "\n\n".join(part for part in parts if part)
    if not task:
        raise SystemExit("Provide a task argument, --task-file, or pipe a task on stdin.")
    return task


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug[:48] or "task"


def make_run_id(task: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{slugify(task)}"


def build_prompt(
    task: str,
    run_id: str,
    runner: str,
    *,
    draft_pr: bool,
    base_branch: str,
) -> str:
    voice_brief_path = f"/tmp/vb-escalation-{run_id}.txt"
    publish_manifest_path = f"/tmp/minion-publish-{run_id}.json"
    pr_instructions = (
        f"""
## Draft PR Mode

This run has explicit approval to prepare a draft pull request after the ticket is implemented and checks pass. The outer minion launcher owns all GitHub publishing.

When the implementation is ready:

1. Do not create a branch, stage files, commit, push, run `gh auth status`, or open a PR from inside the coding-agent sandbox.
2. Leave only the ticket's local file changes in the worktree.
3. Run the narrowest relevant checks.
4. Write a publish manifest to `{publish_manifest_path}` with this exact JSON shape:

   ```json
   {{
     "status": "ready",
     "files": ["README.md"],
     "commit_message": "Add profile readiness scoring copy",
     "pr_title": "GURU-101: Add profile readiness scoring copy",
     "pr_body": "Summary:\\n- ...\\n\\nChecks:\\n- ..."
   }}
   ```

5. `files` must contain only repo-relative paths that belong to this ticket. Do not include unrelated dirty files.
6. The outer launcher will create branch `minion/{run_id}`, stage only manifest-listed files, commit, push, and open a draft PR against `{base_branch}` using the user's normal terminal GitHub auth.
7. If implementation or validation is blocked by a genuine human decision, write the Vocal Bridge escalation brief to `{voice_brief_path}` and stop with `MINION_BLOCKED: {voice_brief_path}`.
"""
        if draft_pr
        else """
## Pull Request Mode

Do not commit, push, or open a pull request in this run. Leave the completed local changes and a concise summary.
"""
    ).strip()

    return f"""# One-Shot Coding Minion

You are a terminal-launched coding minion working in this repository:

`{REPO_ROOT}`

Runner: `{runner}`
Run id: `{run_id}`

## Objective

{task}

## Operating Model

1. Read the relevant repo instructions first, including `AGENTS.md` files that apply to touched paths.
2. Make a short implementation plan, then execute it end to end when the next steps are safe and in scope.
3. Keep changes small and reviewable. Prefer existing project terminology and patterns.
4. Run the narrowest relevant checks before finishing.
5. Do not commit, push, deploy, delete user work, rotate secrets, or change external services unless the task explicitly asks for it or the human approves.

## Voice Escalation

Use the Vocal Bridge escalation skill at:

`{SKILL_PATH}`

Read and follow that skill when you hit a genuine human-only decision. Do not call for ordinary coding/debugging decisions.

If a call is required:

1. Write a concise spoken decision brief to `{voice_brief_path}`.
2. Include stakes, recommended option, alternatives, exact allowed answers, and the safe fallback.
3. Stop and include `MINION_BLOCKED: {voice_brief_path}` in the final response.
4. The outer minion launcher will run `python3 playground/minions/vocal.py --message-file {voice_brief_path}` from outside the coding-agent sandbox.
5. Resume only on a later run after the human answer is clear. If the call fails or the answer is ambiguous, stop before destructive or external actions and report the blocker.

Never print, commit, or speak API keys, tokens, credentials, private file contents, or other secrets.

{pr_instructions}

## Final Response

Return a concise summary with:

- what changed;
- checks run;
- branch/PR information if draft PR mode was enabled;
- any voice escalation used and the decision received;
- any remaining blockers or assumptions.
"""


def require_command(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"`{name}` was not found on PATH.")
    return path


def run_repo_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def git_stdout(args: list[str]) -> str:
    completed = run_repo_command(["git", *args])
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def draft_pr_snapshot() -> dict[str, object]:
    return {
        "branch": git_stdout(["branch", "--show-current"]),
        "head": git_stdout(["rev-parse", "HEAD"]),
        "status": set(git_stdout(["status", "--porcelain=v1"]).splitlines()),
    }


def escalation_brief_path(run_id: str) -> Path:
    return Path(f"/tmp/vb-escalation-{run_id}.txt")


def escalation_answer_path(run_id: str) -> Path:
    return Path(f"/tmp/vb-answer-{run_id}.json")


def publish_manifest_path(run_id: str) -> Path:
    return Path(f"/tmp/minion-publish-{run_id}.json")


def write_publish_blocker_brief(run_id: str, reason: str, base_branch: str) -> Path:
    brief_path = escalation_brief_path(run_id)
    if brief_path.exists() and brief_path.read_text(encoding="utf-8").strip():
        return brief_path

    branch_name = f"minion/{run_id}"
    brief = f"""I'm blocked on publishing the Gurukul coding task.
Stakes: the local implementation may be complete, but draft PR mode cannot finish until the branch, commit, push, and PR are verified.
Blocker: {reason}
Recommended option: pause while you run the required auth or Git permission step locally, then rerun the ticket. The expected publish flow is: gh auth login -h github.com, git switch -c {branch_name}, commit only the ticket changes, git push -u origin {branch_name}, and open a draft PR against {base_branch}.
Alternative: skip the PR and leave the local changes uncommitted for later publishing.
Please answer with "pause", "skip PR", or "stop".
If I do not get a clear answer, I will stop before any external publishing action."""
    brief_path.write_text(brief, encoding="utf-8")
    return brief_path


def parse_allowed_answers_from_brief(brief_text: str) -> list[str]:
    patterns = (
        r"Please answer exactly one of(?:\s+[^:\n]+)?:\s*(.+?)(?:\.|\n|$)",
        r"Please answer with one of(?:\s+[^:\n]+)?:\s*(.+?)(?:\.|\n|$)",
        r"Please answer with\s+(.+?)(?:\.|\n|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, brief_text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        raw = match.group(1)
        raw = raw.replace(" or ", ",").replace(" and ", ",")
        answers: list[str] = []
        for item in raw.split(","):
            cleaned = item.strip().strip("`\"'").lower()
            cleaned = cleaned.split(":", 1)[0].strip()
            cleaned = re.sub(r"\s+", " ", cleaned)
            cleaned = re.sub(r"[^a-z0-9_ -].*$", "", cleaned).strip()
            if cleaned and cleaned not in answers:
                answers.append(cleaned)
        if answers:
            return answers
    return []


def read_escalation_answer(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    answer = str(payload.get("answer", "")).strip().lower()
    if not answer:
        return None
    payload["answer"] = answer
    return payload


def append_human_decision(task: str, answer_payload: dict) -> str:
    answer = str(answer_payload.get("answer", "")).strip()
    source = str(answer_payload.get("source", "voice")).strip()
    session_id = str(answer_payload.get("session_id", "")).strip()
    lines = [
        "## Human Decision From Prior Voice Call",
        "",
        f"The human answered: `{answer}`.",
        "",
        "Use this exact answer to resume the blocker already escalated by voice.",
        "Do not call again for the same decision.",
        "If the answer is not valid for this ticket's allowed options, stop before changing product code and report the blocker.",
        "",
        f"Decision source: {source}.",
    ]
    if session_id:
        lines.append(f"Vocal Bridge session id: {session_id}.")
    return f"{task.rstrip()}\n\n" + "\n".join(lines)


def place_outer_voice_call(
    brief_path: Path,
    *,
    run_id: str,
    await_answer: bool = False,
) -> int:
    if os.environ.get("MINION_DISABLE_OUTER_VOICE") == "1":
        print("\nMINION_DISABLE_OUTER_VOICE=1; skipping Vocal Bridge call.")
        return 0

    command = [
        sys.executable,
        str(MINIONS_DIR / "vocal.py"),
        "--message-file",
        str(brief_path),
        "--show-logs",
    ]
    if await_answer:
        brief_text = brief_path.read_text(encoding="utf-8")
        allowed_answers = parse_allowed_answers_from_brief(brief_text)
        if allowed_answers:
            command.extend(
                [
                    "--await-answer",
                    "--allowed-answers",
                    ",".join(allowed_answers),
                    "--answer-file",
                    str(escalation_answer_path(run_id)),
                ]
            )
        else:
            print("\nNo exact allowed answers found in the brief; placing call without auto-resume.")

    print("\nPlacing Vocal Bridge escalation from the outer minion launcher.")
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        text=True,
    )
    if completed.returncode != 0:
        print(
            f"Outer Vocal Bridge escalation failed with exit {completed.returncode}.",
            file=sys.stderr,
        )
    return completed.returncode


def written_escalation_brief(run_id: str) -> Path | None:
    brief_path = escalation_brief_path(run_id)
    if not brief_path.exists():
        return None

    if not brief_path.read_text(encoding="utf-8").strip():
        return None

    return brief_path


def handle_written_escalation_brief(run_id: str) -> int | None:
    brief_path = written_escalation_brief(run_id)
    if brief_path is None:
        return None

    print(f"\nMINION_BLOCKED_BRIEF: {brief_path}", file=sys.stderr)
    place_outer_voice_call(brief_path, run_id=run_id)
    return BLOCKED_EXIT_CODE


def load_publish_manifest(run_id: str) -> dict:
    path = publish_manifest_path(run_id)
    if not path.exists():
        raise RuntimeError(f"publish manifest was not written: {path}")

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"publish manifest is not valid JSON: {path}") from exc

    if not isinstance(manifest, dict):
        raise RuntimeError("publish manifest must be a JSON object")
    if manifest.get("status") != "ready":
        raise RuntimeError("publish manifest status must be `ready`")
    return manifest


def manifest_files(manifest: dict) -> list[str]:
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError("publish manifest must include a non-empty `files` list")

    clean_files: list[str] = []
    for value in files:
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError("publish manifest file entries must be strings")
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise RuntimeError(f"publish manifest file is not repo-relative: {value}")
        repo_path = REPO_ROOT / path
        if not repo_path.exists():
            raise RuntimeError(f"publish manifest file does not exist: {value}")
        clean_files.append(value)
    return clean_files


def manifest_ticket_key(manifest: dict) -> str | None:
    candidates = [
        manifest.get("pr_title"),
        manifest.get("commit_message"),
        manifest.get("pr_body"),
    ]
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        match = re.search(r"\b([A-Z][A-Z0-9]+-\d+)\b", candidate)
        if match:
            return match.group(1)
    return None


def remote_branches_matching(patterns: list[str]) -> list[str]:
    completed = run_repo_command(["git", "branch", "-r", "--list", *patterns])
    if completed.returncode != 0:
        return []
    branches = [
        line.strip().removeprefix("origin/")
        for line in completed.stdout.splitlines()
        if line.strip()
    ]
    return sorted(set(branches))


def find_existing_pr_handover(manifest: dict, base_branch: str) -> dict | None:
    ticket_key = manifest_ticket_key(manifest)
    pr_title = manifest.get("pr_title")
    search_terms: list[str] = []
    if isinstance(ticket_key, str) and ticket_key.strip():
        search_terms.append(ticket_key.strip())
        search_terms.append(ticket_key.strip().lower())
    if isinstance(pr_title, str) and pr_title.strip():
        search_terms.append(pr_title.strip())

    gh_path = shutil.which("gh")
    if gh_path:
        for term in search_terms:
            completed = run_repo_command(
                [
                    gh_path,
                    "pr",
                    "list",
                    "--state",
                    "open",
                    "--json",
                    "number,url,headRefName,title,baseRefName,isDraft",
                    "--search",
                    term,
                ]
            )
            if completed.returncode != 0:
                continue
            try:
                pulls = json.loads(completed.stdout or "[]")
            except json.JSONDecodeError:
                continue
            if not isinstance(pulls, list):
                continue
            for pull in pulls:
                if not isinstance(pull, dict):
                    continue
                title = str(pull.get("title", ""))
                head_ref = str(pull.get("headRefName", ""))
                pull_base = str(pull.get("baseRefName", ""))
                is_draft = bool(pull.get("isDraft", False))
                if pull_base != base_branch:
                    continue
                if ticket_key and ticket_key.lower() not in (title.lower() + " " + head_ref.lower()):
                    continue
                return {
                    "number": pull.get("number"),
                    "url": pull.get("url"),
                    "headRefName": head_ref,
                    "title": title,
                    "baseRefName": pull_base,
                    "isDraft": is_draft,
                }

    branch_patterns = []
    if isinstance(ticket_key, str) and ticket_key.strip():
        slug = ticket_key.strip().lower()
        branch_patterns.extend([f"*{slug}*", f"*{slug.replace('-', '')}*"])
    if isinstance(pr_title, str) and pr_title.strip():
        branch_patterns.append(f"*{slugify(pr_title)}*")

    branches = remote_branches_matching(branch_patterns)
    if len(branches) == 1:
        return {"headRefName": branches[0]}
    return None


def switch_to_publish_branch(branch_name: str) -> None:
    local_branch = run_repo_command(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"])
    if local_branch.returncode == 0:
        run_publish_command(["git", "switch", branch_name], f"failed to switch to branch `{branch_name}`")
        return

    remote_branch = run_repo_command(
        ["git", "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{branch_name}"]
    )
    if remote_branch.returncode == 0:
        run_publish_command(
            ["git", "switch", "-c", branch_name, "--track", f"origin/{branch_name}"],
            f"failed to switch to tracked branch `{branch_name}`",
        )
        return

    run_publish_command(["git", "switch", "-c", branch_name], f"failed to create branch `{branch_name}`")


def command_output(command: list[str]) -> str:
    completed = run_repo_command(command)
    return (completed.stdout + completed.stderr).strip()


def run_publish_command(command: list[str], blocker_context: str) -> subprocess.CompletedProcess[str]:
    completed = run_repo_command(command)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        message = blocker_context
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message)
    return completed


def ensure_clean_index_for_manifest(files: list[str]) -> None:
    cached = git_stdout(["diff", "--cached", "--name-only"]).splitlines()
    extras = sorted(path for path in cached if path not in files)
    if extras:
        raise RuntimeError(
            "staged files exist outside the publish manifest: " + ", ".join(extras)
        )


def publish_draft_pr_from_manifest(run_id: str, base_branch: str) -> int:
    try:
        manifest = load_publish_manifest(run_id)
        files = manifest_files(manifest)
        ensure_clean_index_for_manifest(files)
        existing_pr = find_existing_pr_handover(manifest, base_branch)
        branch_name = f"minion/{run_id}"
        if existing_pr and existing_pr.get("headRefName"):
            branch_name = str(existing_pr["headRefName"])

        diff_check = run_repo_command(["git", "diff", "--quiet", "--", *files])
        staged_check = run_repo_command(["git", "diff", "--cached", "--quiet", "--", *files])
        if diff_check.returncode == 0 and staged_check.returncode == 0:
            if existing_pr:
                existing_url = existing_pr.get("url") or existing_pr.get("headRefName") or branch_name
                print(
                    "\nManifest-listed files are already present. "
                    f"Handing off existing PR: {existing_url}"
                )
                return 0
            raise RuntimeError("manifest-listed files have no local changes to publish")

        gh_path = require_command("gh")
        run_publish_command([gh_path, "auth", "status"], "GitHub CLI auth is not ready")

        switch_to_publish_branch(branch_name)

        run_publish_command(["git", "add", "--", *files], "failed to stage manifest-listed files")

        commit_message = manifest.get("commit_message") or f"Implement {run_id}"
        if not isinstance(commit_message, str) or not commit_message.strip():
            commit_message = f"Implement {run_id}"
        run_publish_command(["git", "commit", "-m", commit_message.strip()], "failed to commit manifest-listed files")

        run_publish_command(["git", "push", "-u", "origin", branch_name], f"failed to push branch `{branch_name}`")

        pr_title = manifest.get("pr_title") or commit_message.strip()
        if not isinstance(pr_title, str) or not pr_title.strip():
            pr_title = commit_message.strip()
        pr_body = manifest.get("pr_body") or "Draft PR created by minion outer launcher."
        if not isinstance(pr_body, str) or not pr_body.strip():
            pr_body = "Draft PR created by minion outer launcher."

        if existing_pr:
            existing_url = existing_pr.get("url") or branch_name
            print(f"\nExisting PR handed off: {existing_url}")
            return 0

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write(pr_body)
            body_path = handle.name
        try:
            pr_create = run_publish_command(
                [
                    gh_path,
                    "pr",
                    "create",
                    "--draft",
                    "--base",
                    base_branch,
                    "--head",
                    branch_name,
                    "--title",
                    pr_title.strip(),
                    "--body-file",
                    body_path,
                ],
                "failed to create draft PR",
            )
        finally:
            Path(body_path).unlink(missing_ok=True)

        pr_url = pr_create.stdout.strip()
        if pr_url:
            print(f"\nDraft PR created: {pr_url}")
        else:
            print("\nDraft PR created.")
        return 0
    except RuntimeError as exc:
        reason = str(exc)
        print(f"\nMINION_BLOCKED: {reason}", file=sys.stderr)
        brief_path = write_publish_blocker_brief(run_id, reason, base_branch)
        print(f"MINION_BLOCKED_BRIEF: {brief_path}", file=sys.stderr)
        place_outer_voice_call(brief_path, run_id=run_id)
        return BLOCKED_EXIT_CODE


def validate_draft_pr_completion(
    run_id: str,
    base_branch: str,
    before: dict[str, object] | None,
) -> int:
    if before is None:
        return 0

    after = draft_pr_snapshot()
    before_status = before.get("status", set())
    after_status = after.get("status", set())
    new_dirty = sorted(after_status - before_status)
    start_branch = str(before.get("branch") or "")
    current_branch = str(after.get("branch") or "")
    start_head = str(before.get("head") or "")
    current_head = str(after.get("head") or "")

    blocker: str | None = None
    if new_dirty:
        blocker = (
            "draft PR mode ended with new uncommitted work: "
            + ", ".join(new_dirty[:8])
        )
    elif not current_head or current_head == start_head:
        blocker = "draft PR mode ended without creating a new commit."
    elif not current_branch or current_branch == start_branch:
        blocker = "draft PR mode did not switch to a ticket branch."
    else:
        upstream = run_repo_command(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]
        )
        if upstream.returncode != 0:
            blocker = (
                f"branch `{current_branch}` does not have an upstream; push was not verified."
            )

    if blocker is None:
        gh_path = shutil.which("gh")
        if not gh_path:
            blocker = "`gh` is not installed, so the draft PR cannot be verified."
        else:
            pr_view = run_repo_command(
                [
                    gh_path,
                    "pr",
                    "view",
                    current_branch,
                    "--json",
                    "url,state,isDraft,baseRefName,headRefName",
                ]
            )
            if pr_view.returncode != 0:
                detail = (pr_view.stderr or pr_view.stdout).strip()
                blocker = "draft PR was not verified with `gh pr view`."
                if detail:
                    blocker = f"{blocker} {detail}"

    if blocker is None:
        print("\nDraft PR postcondition verified.")
        return 0

    print(f"\nMINION_BLOCKED: {blocker}", file=sys.stderr)
    brief_path = write_publish_blocker_brief(run_id, blocker, base_branch)
    print(f"MINION_BLOCKED_BRIEF: {brief_path}", file=sys.stderr)
    place_outer_voice_call(brief_path, run_id=run_id)
    return BLOCKED_EXIT_CODE


def check_ollama_ready() -> None:
    require_command("ollama")
    completed = subprocess.run(
        ["ollama", "ps"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip()
        message = "Ollama is not reachable. Start it with `ollama serve` in another terminal."
        if detail:
            message = f"{message}\nOllama error: {detail}"
        raise SystemExit(message)


def command_for_runner(
    args: argparse.Namespace, prompt: str, run_id: str, *, preflight: bool
) -> tuple[list[str], str | None]:
    if args.runner == "print":
        return ["printf", "%s", prompt], None

    if args.runner in {"codex", "codex-ollama"}:
        require_command("codex")
        command = [
            "codex",
            "--ask-for-approval",
            "on-request",
            "exec",
            "--cd",
            str(REPO_ROOT),
            "--sandbox",
            "workspace-write",
            "-",
        ]
        if args.runner == "codex-ollama":
            if preflight and os.environ.get("MINION_SKIP_OLLAMA_PREFLIGHT") != "1":
                check_ollama_ready()
            command[1:1] = [
                "--oss",
                "--local-provider",
                "ollama",
                "--model",
                args.model or os.environ.get("OLLAMA_MODEL", "qwen2.5:0.5b"),
            ]
        elif args.model:
            command[1:1] = ["--model", args.model]
        return command, prompt

    if args.runner == "cursor":
        require_command("cursor-agent")
        command = [
            "cursor-agent",
            "--print",
            "--trust",
            "--workspace",
            str(REPO_ROOT),
        ]
        if args.model:
            command.extend(["--model", args.model])
        if args.worktree:
            worktree_name = args.worktree_name or f"voice-minion-{run_id[:40]}"
            command.append(f"--worktree={worktree_name}")
        command.append(prompt)
        return command, None

    raise SystemExit(f"Unsupported runner: {args.runner}")


def write_run_files(run_id: str, prompt: str) -> Path:
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    return run_dir


def print_command(command: list[str]) -> None:
    printable = " ".join(shlex_quote(part) for part in command)
    print(printable)


def shlex_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_@%+=:,./-]+", value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start a one-shot coding minion with voice escalation built in."
    )
    parser.add_argument("task", nargs="*", help="Task for the coding minion.")
    parser.add_argument("--task-file", help="Read the task from a file.")
    parser.add_argument(
        "--runner",
        choices=["codex", "codex-ollama", "cursor", "print"],
        default="codex",
        help="Coding-agent runner to use.",
    )
    parser.add_argument("--model", help="Optional model name for the runner.")
    parser.add_argument(
        "--worktree",
        action="store_true",
        help="Use Cursor Agent's isolated worktree mode. Only applies to --runner cursor.",
    )
    parser.add_argument(
        "--worktree-name",
        help="Cursor worktree name. Only applies with --runner cursor --worktree.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated prompt and runner command without launching an agent.",
    )
    parser.add_argument(
        "--no-run-files",
        action="store_true",
        help="Do not persist the generated prompt under playground/minions/.runs.",
    )
    parser.add_argument(
        "--draft-pr",
        action="store_true",
        help="Publish a draft PR after checks pass; the outer launcher performs Git/GitHub steps.",
    )
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch for draft PR mode.",
    )
    parser.add_argument(
        "--human-decision",
        default="",
        help="Exact human answer from a prior Vocal Bridge escalation.",
    )
    parser.add_argument(
        "--human-decision-note",
        default="",
        help="Optional note about the prior human decision.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task = read_task(args)
    run_id = make_run_id(task)
    prompt = build_prompt(
        task,
        run_id,
        args.runner,
        draft_pr=args.draft_pr,
        base_branch=args.base_branch,
    )
    command, stdin_text = command_for_runner(
        args, prompt, run_id, preflight=not args.dry_run
    )

    if args.dry_run:
        print("Generated minion prompt:\n")
        print(prompt)
        print("\nRunner command:\n")
        print_command(command)
        return 0

    run_dir: Path | None = None
    if not args.no_run_files:
        run_dir = write_run_files(run_id, prompt)
        print(f"Run files: {run_dir}")

    if args.runner == "print":
        print(prompt)
        return 0

    current_task = task
    current_command = command
    current_stdin_text = stdin_text
    max_attempts = 3

    for attempt in range(max_attempts):
        completed = subprocess.run(
            current_command,
            input=current_stdin_text,
            text=True,
            cwd=str(REPO_ROOT),
            env=os.environ.copy(),
        )

        brief_path = written_escalation_brief(run_id)
        if brief_path is not None:
            print(f"\nMINION_BLOCKED_BRIEF: {brief_path}", file=sys.stderr)
            answer_path = escalation_answer_path(run_id)
            answer_path.unlink(missing_ok=True)
            place_outer_voice_call(brief_path, run_id=run_id, await_answer=True)
            answer_payload = read_escalation_answer(answer_path)
            if not answer_payload:
                return BLOCKED_EXIT_CODE

            answer = str(answer_payload.get("answer", "")).strip().lower()
            if answer == "stop":
                print("\nHuman answered `stop`; not resuming implementation.")
                return BLOCKED_EXIT_CODE

            current_task = append_human_decision(current_task, answer_payload)
            resume_prompt = build_prompt(
                current_task,
                run_id,
                args.runner,
                draft_pr=args.draft_pr,
                base_branch=args.base_branch,
            )
            if run_dir is not None:
                (run_dir / f"prompt-resume-{attempt + 1}.md").write_text(
                    resume_prompt,
                    encoding="utf-8",
                )
            brief_path.unlink(missing_ok=True)
            current_command, current_stdin_text = command_for_runner(
                args,
                resume_prompt,
                run_id,
                preflight=False,
            )
            print("\nResuming minion with the captured human decision.")
            continue

        if completed.returncode != 0:
            return completed.returncode

        if args.draft_pr:
            return publish_draft_pr_from_manifest(run_id, args.base_branch)

        return 0

    print("\nMINION_BLOCKED: too many voice escalation resume attempts", file=sys.stderr)
    return BLOCKED_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
