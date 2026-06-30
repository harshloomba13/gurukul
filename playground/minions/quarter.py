#!/usr/bin/env python3
"""Run file-backed Jira-style tickets through coding minions."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import signal
import webbrowser
import subprocess
import sys
import time
import shutil
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


MINIONS_DIR = Path(__file__).resolve().parent
DEFAULT_TICKETS_DIR = MINIONS_DIR / "tickets"
RUNS_DIR = MINIONS_DIR / ".runs" / "quarter"
STATE_PATH = RUNS_DIR / "state.json"
FEEDBACK_PATH = RUNS_DIR / "feedback.jsonl"
IMPROVEMENTS_DIR = RUNS_DIR / "improvements"
BLOCKED_EXIT_CODE = 20
STATE_LOCK = threading.Lock()
DEFAULT_OBSERVER_URL = "http://localhost:3000/observer"
STALE_PROCESS_GRACE_SECONDS = 1.0


@dataclass(frozen=True)
class Ticket:
    path: Path
    key: str
    title: str
    priority: str
    assignee: str
    requires_human_input: bool
    call_only: bool
    human_question: str
    human_options: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_query_param(url: str, key: str, value: str) -> str:
    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params[key] = value
    return urlunparse(parsed._replace(query=urlencode(params)))


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug[:64] or "ticket"


def read_metadata(path: Path) -> Ticket:
    text = path.read_text(encoding="utf-8")
    fields: dict[str, str] = {}

    for line in text.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            break
        key, value = line.split(":", 1)
        fields[key.strip().lower()] = value.strip()

    key = fields.get("key") or path.stem
    title = fields.get("title") or first_heading_or_line(text) or path.stem
    priority = fields.get("priority") or "Unspecified"
    assignee = fields.get("assignee") or "unassigned"
    return Ticket(
        path=path,
        key=key,
        title=title,
        priority=priority,
        assignee=assignee,
        requires_human_input=parse_bool(fields.get("requireshumaninput", "")),
        call_only=parse_bool(fields.get("callonly", "")),
        human_question=fields.get("humanquestion", ""),
        human_options=fields.get("humanoptions", ""),
    )


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def first_heading_or_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        return stripped
    return None


def discover_tickets(tickets_dir: Path) -> list[Ticket]:
    if not tickets_dir.exists():
        raise SystemExit(f"Tickets directory does not exist: {tickets_dir}")

    tickets = [
        read_metadata(path)
        for path in sorted(tickets_dir.glob("*.txt"))
        if path.is_file() and not path.name.startswith(".")
    ]
    if not tickets:
        raise SystemExit(f"No .txt tickets found in {tickets_dir}")
    return tickets


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"tickets": {}}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []

    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            records.append({"raw": line, "parse_error": True})
    return records


def ticket_status(state: dict, ticket: Ticket) -> str:
    record = state.get("tickets", {}).get(ticket.key)
    if not record:
        return "pending"
    return record.get("status", "pending")


def status_for_exit_code(exit_code: int) -> str:
    if exit_code == 0:
        return "done"
    if exit_code == BLOCKED_EXIT_CODE:
        return "blocked"
    return "failed"


def read_process_table() -> dict[int, tuple[int, str]]:
    try:
        completed = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,command="],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError:
        return {}
    if completed.returncode != 0:
        return {}

    processes: dict[int, tuple[int, str]] = {}
    for line in completed.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        pid_text, ppid_text, command = parts
        try:
            pid = int(pid_text)
            ppid = int(ppid_text)
        except ValueError:
            continue
        processes[pid] = (ppid, command)
    return processes


def minions_stale_processes() -> dict[int, str]:
    processes = read_process_table()
    selected: dict[int, str] = {}
    minions_path = str(MINIONS_DIR)
    repo_path = str(MINIONS_DIR.parents[1])

    for pid, (ppid, command) in processes.items():
        if pid == os.getpid():
            continue

        if minions_path in command and "node_modules/.bin/next build" in command:
            selected[pid] = command
            parent = processes.get(ppid)
            if parent:
                _, parent_command = parent
                if parent_command.strip() == "npm run build":
                    selected[ppid] = parent_command
            continue

        if minions_path in command and "/minion.py" in command:
            selected[pid] = command
            continue

        if "codex" in command and " exec " in f" {command} " and f"--cd {repo_path}" in command:
            selected[pid] = command
            continue

        if "cursor-agent" in command and f"--workspace {repo_path}" in command:
            selected[pid] = command

    return include_process_descendants(selected, processes)


def include_process_descendants(
    selected: dict[int, str],
    processes: dict[int, tuple[int, str]],
) -> dict[int, str]:
    expanded = dict(selected)
    changed = True
    while changed:
        changed = False
        for pid, (ppid, command) in processes.items():
            if pid in expanded or ppid not in expanded:
                continue
            expanded[pid] = command
            changed = True
    return expanded


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def cleanup_stale_minions_processes(stage: str, *, enabled: bool) -> None:
    if not enabled:
        return

    stale = minions_stale_processes()
    if not stale:
        return

    print(f"{stage} cleanup: stopping {len(stale)} stale minions process(es).")
    for pid in sorted(stale, reverse=True):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    time.sleep(STALE_PROCESS_GRACE_SECONDS)
    for pid in sorted(stale, reverse=True):
        if not process_exists(pid):
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def extract_pr_handoff(
    log_path: Path,
    *,
    draft_pr: bool,
    exit_code: int,
) -> dict[str, str] | None:
    if not draft_pr:
        return None

    lines = [
        line.strip()
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    ]

    for line in reversed(lines):
        lowered = line.lower()
        if (
            "draft pr created:" in lowered
            or "existing pr handed off:" in lowered
            or "handing off existing pr:" in lowered
        ):
            url = extract_pr_url(line)
            if url:
                return {"status": "created", "url": url}
            return {
                "status": "created",
                "reason": "draft PR was created, but no URL was printed",
            }
        if lowered == "draft pr created.":
            return {
                "status": "created",
                "reason": "draft PR was created, but no URL was printed",
            }

    for line in reversed(lines):
        url = extract_pr_url(line)
        if url:
            return {"status": "created", "url": url}

    for line in reversed(lines):
        if line.startswith("MINION_BLOCKED:"):
            reason = line.split(":", 1)[1].strip()
            return {
                "status": "blocked",
                "reason": reason or "minion reported a blocker before draft PR creation",
            }

    if exit_code == BLOCKED_EXIT_CODE:
        return {
            "status": "blocked",
            "reason": "ticket was blocked before a draft PR was created; inspect the ticket log",
        }
    if exit_code != 0:
        return {
            "status": "not_created",
            "reason": f"ticket exited {exit_code} before a draft PR was created; inspect the ticket log",
        }
    return {
        "status": "not_created",
        "reason": "draft PR was requested, but no PR handoff was found in the ticket log",
    }


def extract_pr_url(text: str) -> str | None:
    match = re.search(r"https://github\.com/[^\s)]+/pull/\d+", text)
    if not match:
        return None
    return match.group(0).rstrip(".,")


def print_ticket_pr_handoff(ticket_key: str, pr_handoff: dict[str, str] | None) -> None:
    if not pr_handoff:
        return

    status = pr_handoff.get("status")
    url = pr_handoff.get("url")
    reason = pr_handoff.get("reason")
    if status == "created" and url:
        print(f"{ticket_key} PR: {url}")
    elif status == "created":
        print(f"{ticket_key} PR: created ({reason or 'URL unavailable'})")
    elif status == "blocked":
        print(f"{ticket_key} PR blocked: {reason or 'no reason captured'}")
    else:
        print(f"{ticket_key} PR not created: {reason or 'no reason captured'}")


def print_tickets(tickets: list[Ticket], state: dict) -> None:
    print("Ticket queue:")
    for ticket in tickets:
        status = ticket_status(state, ticket)
        print(
            f"- {ticket.key:12} {status:10} {ticket.priority:10} "
            f"{ticket.assignee:12} {ticket.title}"
        )


def human_decision_for_ticket(state: dict, ticket: Ticket) -> dict | None:
    record = state.get("tickets", {}).get(ticket.key)
    if not isinstance(record, dict):
        return None

    decision = record.get("human_decision")
    if not isinstance(decision, dict):
        return None

    answer = str(decision.get("answer", "")).strip()
    if not answer:
        return None
    return decision


def build_minion_command(
    args: argparse.Namespace,
    ticket: Ticket,
    human_decision: dict | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(MINIONS_DIR / "minion.py"),
        "--task-file",
        str(ticket.path),
        "--runner",
        args.runner,
        "--base-branch",
        args.base_branch,
    ]

    if args.model:
        command.extend(["--model", args.model])
    if args.runner == "cursor" and args.worktree:
        command.append("--worktree")
        command.extend(["--worktree-name", f"ticket-{slugify(ticket.key)}"])
    if args.draft_pr:
        command.append("--draft-pr")
    if human_decision:
        answer = str(human_decision.get("answer", "")).strip()
        if answer:
            command.extend(["--human-decision", answer])
        note = str(human_decision.get("note", "")).strip()
        if note:
            command.extend(["--human-decision-note", note])

    return command


def selected_tickets(args: argparse.Namespace, tickets: list[Ticket], state: dict) -> list[Ticket]:
    selected = tickets
    if args.ticket:
        wanted = set(args.ticket)
        selected = [
            ticket
            for ticket in selected
            if ticket.key in wanted or ticket.path.name in wanted or ticket.path.stem in wanted
        ]
        missing = wanted - {
            value
            for ticket in selected
            for value in (ticket.key, ticket.path.name, ticket.path.stem)
        }
        if missing:
            raise SystemExit(f"Ticket not found: {', '.join(sorted(missing))}")

    if getattr(args, "assigned_to", None):
        wanted_assignees = {normalize_assignee(value) for value in args.assigned_to}
        selected = [
            ticket
            for ticket in selected
            if normalize_assignee(ticket.assignee) in wanted_assignees
        ]

    if getattr(args, "only_assigned", False):
        selected = [
            ticket
            for ticket in selected
            if normalize_assignee(ticket.assignee) not in {"", "unassigned", "none"}
        ]

    if not args.include_done:
        selected = [ticket for ticket in selected if ticket_status(state, ticket) != "done"]

    if not getattr(args, "include_running", False):
        selected = [ticket for ticket in selected if ticket_status(state, ticket) != "running"]

    if not getattr(args, "include_blocked", False):
        selected = [ticket for ticket in selected if ticket_status(state, ticket) != "blocked"]

    if args.limit:
        selected = selected[: args.limit]

    return selected


def normalize_assignee(value: str) -> str:
    return value.strip().lower()


def open_observer_session(run_id: str) -> None:
    observer_url = os.environ.get("QUARTER_OBSERVER_URL", DEFAULT_OBSERVER_URL)
    observer_url = add_query_param(observer_url, "run", run_id)
    observer_url = add_query_param(observer_url, "autostart", "1")
    print(f"Observer session: {observer_url}")
    opened = webbrowser.open(observer_url, new=1, autoraise=True)
    if not opened:
        print("Browser did not open automatically; open the observer URL manually.")


def workspace_changed_paths(root: Path) -> set[str]:
    tracked = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    deleted = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=D"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    paths = {
        line.strip()
        for output in (tracked.stdout, deleted.stdout, untracked.stdout)
        for line in output.splitlines()
        if line.strip()
    }
    return paths


def should_copy_workspace_path(relative_path: str) -> bool:
    parts = Path(relative_path).parts
    if not parts:
        return False
    if parts[0] == ".git":
        return False
    if parts[0] == ".runs":
        return False
    if parts[0].startswith(".env"):
        return False
    if parts[0] in {".venv", "node_modules", ".next"}:
        return False
    return True


def overlay_workspace_changes(source_root: Path, worktree_dir: Path) -> None:
    for relative_path in sorted(workspace_changed_paths(source_root)):
        if not should_copy_workspace_path(relative_path):
            continue
        source = source_root / relative_path
        destination = worktree_dir / relative_path
        if not source.exists():
            if destination.exists():
                if destination.is_dir() and not destination.is_symlink():
                    shutil.rmtree(destination, ignore_errors=True)
                else:
                    destination.unlink(missing_ok=True)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            if destination.exists():
                shutil.rmtree(destination, ignore_errors=True)
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)


def create_ticket_worktree(ticket: Ticket) -> tuple[Path, Path]:
    parent_dir = Path(
        tempfile.mkdtemp(prefix=f"gurukul-{slugify(ticket.key)}-", dir=tempfile.gettempdir())
    )
    worktree_dir = parent_dir / "repo"
    worktree_dir.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["git", "worktree", "add", "--detach", str(worktree_dir), "HEAD"],
        cwd=str(MINIONS_DIR.parents[1]),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stdout or "").strip()
        shutil.rmtree(parent_dir, ignore_errors=True)
        message = f"Failed to create worktree for {ticket.key}."
        if detail:
            message = f"{message} {detail}"
        raise SystemExit(message)

    overlay_workspace_changes(MINIONS_DIR.parents[1], worktree_dir)
    return worktree_dir, parent_dir


def cleanup_ticket_worktree(worktree_dir: Path, parent_dir: Path) -> None:
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree_dir)],
        cwd=str(MINIONS_DIR.parents[1]),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    shutil.rmtree(parent_dir, ignore_errors=True)


def run_ticket(
    args: argparse.Namespace,
    ticket: Ticket,
    state: dict,
    quarter_run_dir: Path,
    *,
    repo_root: Path | None = None,
    cleanup_dir: Path | None = None,
) -> int:
    previous_record = state.get("tickets", {}).get(ticket.key)
    previous_record = previous_record if isinstance(previous_record, dict) else {}
    human_decision = human_decision_for_ticket(state, ticket)
    command = build_minion_command(args, ticket, human_decision)
    log_path = quarter_run_dir / f"{slugify(ticket.key)}.log"
    record = {
        "status": "running",
        "title": ticket.title,
        "priority": ticket.priority,
        "assignee": ticket.assignee,
        "ticket_file": str(ticket.path),
        "started_at": now_iso(),
        "log": str(log_path),
        "command": command,
    }
    if repo_root is not None:
        record["worktree"] = str(repo_root)
    if human_decision:
        record["human_decision"] = human_decision
        record["resumed_from"] = {
            "status": previous_record.get("status", "unknown"),
            "log": previous_record.get("log"),
        }
    with STATE_LOCK:
        state.setdefault("tickets", {})[ticket.key] = record
        save_state(state)

    print(f"\nAssigning {ticket.key}: {ticket.title}")
    print(f"Log: {log_path}")

    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            call_exit_code = 0
            if ticket.requires_human_input:
                call_exit_code = call_for_ticket(ticket, quarter_run_dir, log_file)
                if call_exit_code != 0:
                    process_returncode = BLOCKED_EXIT_CODE
                elif ticket.call_only:
                    process_returncode = 0
                else:
                    process_returncode = run_minion_command(
                        command,
                        log_file,
                        cwd=repo_root,
                    )
            else:
                process_returncode = run_minion_command(command, log_file, cwd=repo_root)
    finally:
        if cleanup_dir is not None and repo_root is not None:
            cleanup_ticket_worktree(repo_root, cleanup_dir)

    pr_handoff = extract_pr_handoff(
        log_path,
        draft_pr=bool(getattr(args, "draft_pr", False)),
        exit_code=process_returncode,
    )
    with STATE_LOCK:
        record["finished_at"] = now_iso()
        record["exit_code"] = process_returncode
        record["status"] = status_for_exit_code(process_returncode)
        if pr_handoff:
            record["pr_handoff"] = pr_handoff
        save_state(state)

    print(f"{ticket.key} -> {record['status']} (exit {process_returncode})")
    print_ticket_pr_handoff(ticket.key, record.get("pr_handoff"))
    return process_returncode


def run_minion_command(
    command: list[str],
    log_file,
    *,
    cwd: Path | None = None,
) -> int:
    env = os.environ.copy()
    if cwd is not None:
        env["MINION_REPO_ROOT"] = str(cwd)
    process = subprocess.run(
        command,
        cwd=str(cwd or MINIONS_DIR),
        env=env,
        text=True,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    return process.returncode


def execute_ticket_batch(
    args: argparse.Namespace,
    tickets: list[Ticket],
    state: dict,
    quarter_run_dir: Path,
) -> int:
    if not tickets:
        return 0

    if getattr(args, "sequential", False) or len(tickets) == 1:
        failed = 0
        for ticket in tickets:
            exit_code = run_ticket(args, ticket, state, quarter_run_dir)
            if exit_code != 0:
                failed += 1
                if args.stop_on_failure:
                    break
        return failed

    prepared_worktrees: dict[str, tuple[Path, Path]] = {}
    for ticket in tickets:
        prepared_worktrees[ticket.key] = create_ticket_worktree(ticket)

    failed = 0
    futures: dict[concurrent.futures.Future[int], Ticket] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tickets)) as executor:
        for ticket in tickets:
            worktree_dir, parent_dir = prepared_worktrees[ticket.key]
            futures[executor.submit(
                run_ticket,
                args,
                ticket,
                state,
                quarter_run_dir,
                repo_root=worktree_dir,
                cleanup_dir=parent_dir,
            )] = ticket

        for future in concurrent.futures.as_completed(futures):
            ticket = futures[future]
            try:
                exit_code = future.result()
            except Exception as exc:  # pragma: no cover - surfaced in logs
                failed += 1
                print(f"{ticket.key} -> failed with exception: {exc}")
                if args.stop_on_failure:
                    break
                continue

            if exit_code != 0:
                failed += 1
                if args.stop_on_failure:
                    break

    return failed


def call_for_ticket(ticket: Ticket, quarter_run_dir: Path, log_file) -> int:
    brief_path = quarter_run_dir / f"{slugify(ticket.key)}-voice-brief.txt"
    question = ticket.human_question or (
        "This ticket is intentionally blocked until the human confirms the voice escalation path."
    )
    options = ticket.human_options or "approve, stop"
    brief = (
        f"I'm blocked on ticket {ticket.key}: {ticket.title}.\n"
        f"Stakes: this is a Vocal Bridge call-path test for assigned minion tickets.\n"
        f"Question: {question}\n"
        f"Please answer with one of: {options}.\n"
        "If I do not get a clear answer, I will stop before doing any ticket work.\n"
    )
    brief_path.write_text(brief, encoding="utf-8")

    log_file.write("RequiresHumanInput is true; placing Vocal Bridge escalation call.\n")
    log_file.write(f"Voice brief: {brief_path}\n\n")
    log_file.flush()

    process = subprocess.run(
        [
            sys.executable,
            str(MINIONS_DIR / "vocal.py"),
            "--message-file",
            str(brief_path),
            "--show-logs",
        ],
        cwd=str(MINIONS_DIR),
        env=os.environ.copy(),
        text=True,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    if process.returncode == 0 and ticket.call_only:
        log_file.write("\nCallOnly is true; stopping after call-path validation.\n")
    return process.returncode


def cmd_list(args: argparse.Namespace) -> int:
    tickets = discover_tickets(Path(args.tickets_dir))
    state = load_state()
    print_tickets(tickets, state)
    return 0


def find_ticket(identifier: str, tickets: list[Ticket]) -> Ticket:
    for ticket in tickets:
        if identifier in {ticket.key, ticket.path.name, ticket.path.stem}:
            return ticket
    raise SystemExit(f"Ticket not found: {identifier}")


def cmd_plan(args: argparse.Namespace) -> int:
    tickets = discover_tickets(Path(args.tickets_dir))
    state = load_state()
    selected = selected_tickets(args, tickets, state)
    if not selected:
        print("No pending tickets selected.")
        return 0

    print("Planned minion assignments:")
    for ticket in selected:
        print(f"\n{ticket.key}: {ticket.title}")
        command = build_minion_command(args, ticket, human_decision_for_ticket(state, ticket))
        print(" ".join(shell_quote(part) for part in command))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    tickets = discover_tickets(Path(args.tickets_dir))
    state = load_state()
    selected = selected_tickets(args, tickets, state)
    if not selected:
        print("No pending tickets selected.")
        return 0

    cleanup_enabled = not getattr(args, "skip_process_cleanup", False)
    cleanup_stale_minions_processes("Pre-run", enabled=cleanup_enabled)

    quarter_run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    quarter_run_dir = RUNS_DIR / quarter_run_id
    quarter_run_dir.mkdir(parents=True, exist_ok=False)

    print(f"Quarter run: {quarter_run_dir}")
    print(f"Tickets: {len(selected)}")
    open_observer_session(quarter_run_id)

    try:
        failed = execute_ticket_batch(args, selected, state, quarter_run_dir)
    finally:
        cleanup_stale_minions_processes("Post-run", enabled=cleanup_enabled)

    print(f"\nComplete. Failed tickets: {failed}")
    return 1 if failed else 0


def cmd_watch(args: argparse.Namespace) -> int:
    print("Watching for assigned tickets.")
    print(f"Tickets dir: {Path(args.tickets_dir)}")
    print(f"Poll interval: {args.interval}s")
    if args.assigned_to:
        print(f"Assignees: {', '.join(args.assigned_to)}")
    elif args.only_assigned:
        print("Assignees: any non-empty assignee")
    else:
        print("Assignees: all tickets")

    cleanup_enabled = not getattr(args, "skip_process_cleanup", False)
    cleanup_stale_minions_processes("Pre-watch", enabled=cleanup_enabled)

    loops = 0
    observer_opened = False
    while True:
        tickets = discover_tickets(Path(args.tickets_dir))
        state = load_state()
        selected = selected_tickets(args, tickets, state)

        if selected:
            quarter_run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            quarter_run_dir = RUNS_DIR / quarter_run_id
            quarter_run_dir.mkdir(parents=True, exist_ok=False)
            print(f"\nFound {len(selected)} assigned ticket(s). Run: {quarter_run_dir}")
            if not observer_opened:
                open_observer_session(quarter_run_id)
                observer_opened = True

            try:
                failed = execute_ticket_batch(args, selected, state, quarter_run_dir)
            finally:
                cleanup_stale_minions_processes("Post-watch", enabled=cleanup_enabled)
            if failed and args.stop_on_failure:
                return 1
        else:
            print(f"{now_iso()} no matching pending tickets")

        loops += 1
        if args.once or (args.max_loops and loops >= args.max_loops):
            return 0
        time.sleep(args.interval)


def cmd_reset(args: argparse.Namespace) -> int:
    state = load_state()
    tickets = discover_tickets(Path(args.tickets_dir))
    if not args.ticket:
        reset_keys = {ticket.key for ticket in tickets}
        ticket_state = state.setdefault("tickets", {})
        for key in reset_keys:
            if key in ticket_state:
                ticket_state.pop(key, None)
        save_state(state)
        print(f"Reset ticket state for {len(reset_keys)} ticket file(s).")
        return 0

    wanted = set(args.ticket)
    selected_keys = {
        ticket.key
        for ticket in tickets
        if ticket.key in wanted or ticket.path.name in wanted or ticket.path.stem in wanted
    }
    missing = wanted - {
        value
        for ticket in tickets
        if ticket.key in selected_keys
        for value in (ticket.key, ticket.path.name, ticket.path.stem)
    }
    if missing:
        raise SystemExit(f"Ticket not found: {', '.join(sorted(missing))}")

    ticket_state = state.setdefault("tickets", {})
    for key in selected_keys:
        ticket_state.pop(key, None)
    save_state(state)
    if selected_keys:
        print(f"Reset ticket state for: {', '.join(sorted(selected_keys))}")
    else:
        print("No matching ticket state to reset.")
    return 0


def cmd_answer(args: argparse.Namespace) -> int:
    tickets = discover_tickets(Path(args.tickets_dir))
    ticket = find_ticket(args.ticket, tickets)
    state = load_state()
    record = state.setdefault("tickets", {}).setdefault(ticket.key, {})
    previous_status = record.get("status", "pending")
    created_at = now_iso()

    record.update(
        {
            "status": "pending",
            "title": ticket.title,
            "priority": ticket.priority,
            "assignee": ticket.assignee,
            "ticket_file": str(ticket.path),
            "human_decision": {
                "answer": args.answer.strip(),
                "note": args.note.strip(),
                "source": args.source.strip(),
                "created_at": created_at,
                "previous_status": previous_status,
            },
            "answered_at": created_at,
        }
    )
    save_state(state)
    print(f"Recorded human decision for {ticket.key}: {args.answer.strip()}")
    print(f"{ticket.key} is pending and ready to resume.")
    return 0


def shell_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_@%+=:,./-]+", value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def recent_ticket_logs(limit: int, ticket_key: str | None = None) -> list[Path]:
    if not RUNS_DIR.exists():
        return []

    logs: list[Path] = []
    for run_dir in sorted((path for path in RUNS_DIR.iterdir() if path.is_dir()), reverse=True):
        for log_path in sorted(run_dir.glob("*.log")):
            if ticket_key and slugify(ticket_key) != log_path.stem:
                continue
            logs.append(log_path)
            if len(logs) >= limit:
                return logs
    return logs


def extract_log_signals(log_path: Path) -> list[str]:
    patterns = (
        "minion_blocked",
        "blocked",
        "failed",
        "error:",
        "vocal bridge",
        "outbound call",
        "gh auth",
        "invalid",
        "draft pr",
        "exit ",
    )
    signals: list[str] = []
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        lowered = line.lower()
        if any(pattern in lowered for pattern in patterns):
            cleaned = line.strip()
            if cleaned:
                signals.append(cleaned[:240])
        if len(signals) >= 16:
            break
    return signals


def build_improvement_recommendations(
    feedback: list[dict],
    log_summaries: list[dict],
) -> list[str]:
    combined = "\n".join(
        [
            *(str(item.get("note", "")) for item in feedback),
            *(signal for summary in log_summaries for signal in summary["signals"]),
        ]
    ).lower()

    recommendations: list[str] = []
    if "outbound call initiated" in combined or "vocal bridge" in combined:
        recommendations.append(
            "Store the Vocal Bridge call id/session id in ticket state so the outer loop can connect a call outcome to the blocked run."
        )
    if "gh auth" in combined or "github cli auth" in combined or "invalid" in combined:
        recommendations.append(
            "Keep GitHub auth as a human-only blocker and prefer a short AUTH/SKIP_PR/STOP voice brief before any staging or push."
        )
    if "done" in combined and "blocked" in combined:
        recommendations.append(
            "Add or preserve postcondition checks that mark incomplete publish work as blocked instead of done."
        )
    if "system prompt" in combined or "greeting" in combined or "real problem" in combined:
        recommendations.append(
            "Use a generic dashboard outbound greeting and set the live agent prompt from the escalation brief before each call."
        )
    if not feedback:
        recommendations.append(
            "Collect human feedback with `quarter.py feedback` after each surprising run; the improve loop is more useful with explicit notes."
        )
    if not recommendations:
        recommendations.append(
            "No high-confidence workflow change found. Review the run logs and feedback before editing Skills."
        )
    return recommendations


def write_improvement_report(
    *,
    ticket_key: str | None,
    feedback: list[dict],
    log_summaries: list[dict],
    recommendations: list[str],
) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = IMPROVEMENTS_DIR / f"{stamp}-improvement-report.md"
    IMPROVEMENTS_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Minion Self-Improvement Report",
        "",
        f"Generated: {now_iso()}",
        f"Ticket filter: {ticket_key or 'all'}",
        "",
        "## Recommendations",
        "",
    ]
    lines.extend(f"- {item}" for item in recommendations)

    lines.extend(["", "## Feedback", ""])
    if feedback:
        for item in feedback:
            lines.append(
                f"- {item.get('created_at', 'unknown')} {item.get('ticket', 'unknown')} "
                f"{item.get('rating', 'note')} [{item.get('category', 'general')}]: "
                f"{item.get('note', item.get('raw', ''))}"
            )
    else:
        lines.append("- No feedback records matched this run.")

    lines.extend(["", "## Recent Run Signals", ""])
    if log_summaries:
        for summary in log_summaries:
            lines.append(f"### {summary['log']}")
            if summary["signals"]:
                lines.extend(f"- {signal}" for signal in summary["signals"])
            else:
                lines.append("- No blocker/failure signals found.")
            lines.append("")
    else:
        lines.append("- No run logs matched this query.")

    lines.extend(
        [
            "## Guardrails",
            "",
            "- This report does not change Skills or workflow code automatically.",
            "- Review proposed changes before editing `SKILL.md`, `minion.py`, or `quarter.py`.",
            "- Do not include secrets, API keys, call recordings, or private transcript content in Skill diffs.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def cmd_feedback(args: argparse.Namespace) -> int:
    record = {
        "created_at": now_iso(),
        "ticket": args.ticket,
        "rating": args.rating,
        "category": args.category,
        "note": args.note,
    }
    if args.run_log:
        record["run_log"] = args.run_log
    append_jsonl(FEEDBACK_PATH, record)
    print(f"Recorded feedback for {args.ticket}: {FEEDBACK_PATH}")
    return 0


def cmd_improve(args: argparse.Namespace) -> int:
    feedback = [
        item
        for item in load_jsonl(FEEDBACK_PATH)
        if not args.ticket or item.get("ticket") == args.ticket
    ]
    logs = recent_ticket_logs(args.last, args.ticket)
    log_summaries = [
        {"log": str(path), "signals": extract_log_signals(path)}
        for path in logs
    ]
    recommendations = build_improvement_recommendations(feedback, log_summaries)
    report_path = write_improvement_report(
        ticket_key=args.ticket,
        feedback=feedback,
        log_summaries=log_summaries,
        recommendations=recommendations,
    )
    print(f"Wrote improvement report: {report_path}")
    print("Top recommendations:")
    for item in recommendations[:3]:
        print(f"- {item}")
    return 0


def add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--tickets-dir",
        default=str(DEFAULT_TICKETS_DIR),
        help="Directory containing Jira-style .txt ticket files.",
    )
    parser.add_argument(
        "--ticket",
        action="append",
        help="Ticket key, filename, or stem to select. Repeat to select multiple.",
    )
    parser.add_argument("--limit", type=int, help="Maximum number of tickets to select.")
    parser.add_argument(
        "--include-done",
        action="store_true",
        help="Include tickets already marked done in state.",
    )
    parser.add_argument(
        "--include-running",
        action="store_true",
        help="Include tickets currently marked running in state.",
    )
    parser.add_argument(
        "--include-blocked",
        action="store_true",
        help="Include tickets currently marked blocked in state.",
    )
    parser.add_argument(
        "--assigned-to",
        action="append",
        help="Only select tickets assigned to this value. Repeat for multiple assignees.",
    )
    parser.add_argument(
        "--only-assigned",
        action="store_true",
        help="Only select tickets with a non-empty assignee.",
    )
    parser.add_argument(
        "--runner",
        choices=["codex", "codex-ollama", "cursor", "print"],
        default="codex",
        help="Minion runner to use.",
    )
    parser.add_argument("--model", help="Optional model for the minion runner.")
    parser.add_argument(
        "--worktree",
        action="store_true",
        help="Use Cursor Agent worktree mode. Only applies with --runner cursor.",
    )
    parser.add_argument(
        "--draft-pr",
        action="store_true",
        help="Tell each minion to open a draft PR after implementing its ticket.",
    )
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch for draft PR mode.",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assign local Jira-style ticket files to coding minions."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="Show ticket state.")
    list_parser.add_argument(
        "--tickets-dir",
        default=str(DEFAULT_TICKETS_DIR),
        help="Directory containing Jira-style .txt ticket files.",
    )
    list_parser.set_defaults(func=cmd_list)

    plan_parser = subparsers.add_parser("plan", help="Print planned minion commands.")
    add_common_options(plan_parser)
    plan_parser.set_defaults(func=cmd_plan)

    run_parser = subparsers.add_parser("run", help="Run selected tickets.")
    add_common_options(run_parser)
    run_parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop after the first failed ticket.",
    )
    run_parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run tickets one at a time instead of in parallel.",
    )
    run_parser.add_argument(
        "--skip-process-cleanup",
        action="store_true",
        help="Skip pre/post cleanup of stale minions-owned runner/build processes.",
    )
    run_parser.set_defaults(func=cmd_run)

    watch_parser = subparsers.add_parser(
        "watch", help="Continuously run newly assigned tickets."
    )
    add_common_options(watch_parser)
    watch_parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Polling interval in seconds.",
    )
    watch_parser.add_argument(
        "--once",
        action="store_true",
        help="Poll once and exit. Useful for testing assignment filters.",
    )
    watch_parser.add_argument(
        "--max-loops",
        type=int,
        help="Stop after this many polling loops.",
    )
    watch_parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop after the first failed ticket.",
    )
    watch_parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run tickets one at a time instead of in parallel.",
    )
    watch_parser.add_argument(
        "--skip-process-cleanup",
        action="store_true",
        help="Skip pre/post cleanup of stale minions-owned runner/build processes.",
    )
    watch_parser.set_defaults(func=cmd_watch)

    reset_parser = subparsers.add_parser("reset", help="Reset local ticket state.")
    reset_parser.add_argument(
        "--tickets-dir",
        default=str(DEFAULT_TICKETS_DIR),
        help="Directory containing Jira-style .txt ticket files.",
    )
    reset_parser.add_argument(
        "--ticket",
        action="append",
        help="Ticket key, filename, or stem to reset. Omit to reset all ticket files in the tickets directory.",
    )
    reset_parser.set_defaults(func=cmd_reset)

    answer_parser = subparsers.add_parser(
        "answer", help="Record a human voice decision and mark a blocked ticket ready to resume."
    )
    answer_parser.add_argument(
        "--tickets-dir",
        default=str(DEFAULT_TICKETS_DIR),
        help="Directory containing Jira-style .txt ticket files.",
    )
    answer_parser.add_argument("--ticket", required=True, help="Ticket key, filename, or stem.")
    answer_parser.add_argument("--answer", required=True, help="Exact human answer from the call.")
    answer_parser.add_argument(
        "--source",
        default="voice",
        help="Decision source, for example voice, transcript, or manual.",
    )
    answer_parser.add_argument(
        "--note",
        default="",
        help="Optional note about the decision.",
    )
    answer_parser.set_defaults(func=cmd_answer)

    feedback_parser = subparsers.add_parser(
        "feedback", help="Record human feedback for a ticket run."
    )
    feedback_parser.add_argument("--ticket", required=True, help="Ticket key.")
    feedback_parser.add_argument(
        "--rating",
        choices=["good", "bad", "mixed", "note"],
        default="note",
        help="Overall feedback rating.",
    )
    feedback_parser.add_argument(
        "--category",
        default="general",
        help="Feedback category, for example voice, status, quality, or publish.",
    )
    feedback_parser.add_argument("--note", required=True, help="Feedback note.")
    feedback_parser.add_argument("--run-log", help="Optional path to the run log.")
    feedback_parser.set_defaults(func=cmd_feedback)

    improve_parser = subparsers.add_parser(
        "improve", help="Summarize recent runs and feedback into a reviewable improvement report."
    )
    improve_parser.add_argument(
        "--ticket",
        help="Only inspect feedback and logs for this ticket key.",
    )
    improve_parser.add_argument(
        "--last",
        type=int,
        default=10,
        help="Maximum number of recent ticket logs to inspect.",
    )
    improve_parser.set_defaults(func=cmd_improve)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
