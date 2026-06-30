#!/usr/bin/env python3
"""Place a Vocal Bridge escalation for coding-agent decisions.

This helper is intentionally small: it loads the minions environment, prepares a
voice-ready brief, sets the live agent prompt for that brief, checks the `vb`
CLI, and then either places a phone call or opens the browser voice session.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import fcntl
import webbrowser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


MINIONS_DIR = Path(__file__).resolve().parent
REPO_ROOT = MINIONS_DIR.parents[1]
DEFAULT_ENV_FILE = MINIONS_DIR / ".env.local"
CALL_LOCK_PATH = Path(tempfile.gettempdir()) / "gurukul-vocal-bridge-call.lock"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
SESSION_ID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def read_message(args: argparse.Namespace) -> str:
    if args.message:
        return args.message.strip()

    if args.message_file:
        return Path(args.message_file).read_text(encoding="utf-8").strip()

    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    raise SystemExit("Provide --message, --message-file, or pipe a message on stdin.")


def mask_phone(phone: str) -> str:
    digits = [char for char in phone if char.isdigit()]
    if len(digits) < 4:
        return "***"
    return f"***{''.join(digits[-4:])}"


def add_query_param(url: str, key: str, value: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[key] = value
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def find_vb() -> str | None:
    path_vb = shutil.which("vb")
    if path_vb:
        return path_vb

    repo_vb = REPO_ROOT / ".venv" / "bin" / "vb"
    if repo_vb.exists():
        return str(repo_vb)

    return None


def require_vb() -> str:
    vb_path = find_vb()
    if vb_path:
        return vb_path

    raise SystemExit(
        "The `vb` CLI was not found. Install/authenticate Vocal Bridge CLI "
        "before placing escalation calls."
    )


def run_vb(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    vb_path = require_vb()
    return subprocess.run(
        [vb_path, *args],
        check=check,
        env=os.environ.copy(),
        text=True,
    )


def capture_vb(args: list[str]) -> subprocess.CompletedProcess[str]:
    vb_path = require_vb()
    return subprocess.run(
        [vb_path, *args],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def select_configured_agent() -> None:
    agent_id = os.environ.get("VOCAL_BRIDGE_AGENT_ID")
    if not agent_id:
        return

    print("\nSelecting configured Vocal Bridge agent.")
    run_vb(["agent", "use", agent_id])


def build_agent_prompt(brief: str) -> str:
    return textwrap.dedent(
        f"""
        You are calling the project owner because their coding agent is blocked
        on a human decision.

        Read the decision brief clearly. Ask the owner to answer with one of the
        exact options in the brief. If the answer is unclear, ask one concise
        follow-up. Do not ask for secrets, API keys, or private file contents.

        Decision brief:
        {brief}
        """
    ).strip()


def open_browser_session(url: str) -> None:
    print(f"\nOpening browser session: {url}")
    opened = webbrowser.open(url, new=1, autoraise=True)
    if not opened:
        print(
            "Browser launch did not report success. Open the URL manually if needed.",
            file=sys.stderr,
        )


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def parse_allowed_answers(value: str) -> list[str]:
    answers: list[str] = []
    for item in re.split(r"[,|]", value):
        cleaned = item.strip().strip("`\"'").lower()
        if cleaned and cleaned not in answers:
            answers.append(cleaned)
    return answers


def parse_session_ids(logs_output: str) -> list[str]:
    ids: list[str] = []
    for line in strip_ansi(logs_output).splitlines():
        match = SESSION_ID_RE.search(line)
        if not match:
            continue
        session_id = match.group(0)
        if session_id not in ids:
            ids.append(session_id)
    return ids


def transcript_user_lines(transcript: str) -> list[str]:
    lines = []
    for line in strip_ansi(transcript).splitlines():
        lowered = line.lower()
        if any(marker in lowered for marker in ("user", "human", "caller", "callee", "participant")):
            lines.append(line)
    return lines


def extract_allowed_answer(transcript: str, allowed_answers: list[str]) -> str | None:
    if not allowed_answers:
        return None

    patterns = {
        answer: re.compile(rf"(?<![a-z0-9_-]){re.escape(answer)}(?![a-z0-9_-])", re.IGNORECASE)
        for answer in allowed_answers
    }

    user_text = "\n".join(transcript_user_lines(transcript))
    if user_text:
        matches = [answer for answer, pattern in patterns.items() if pattern.search(user_text)]
        if len(matches) == 1:
            return matches[0]

    prompt_markers = (
        "decision brief",
        "stakes:",
        "recommended option",
        "alternative",
        "alternatives",
        "please answer",
        "allowed",
        "if i do not",
        "exactly one",
        "option",
        "means ",
    )
    for line in reversed(strip_ansi(transcript).splitlines()):
        stripped_line = line.strip()
        if not stripped_line:
            continue
        lowered = stripped_line.lower()
        if any(marker in lowered for marker in prompt_markers):
            continue
        matches = [answer for answer, pattern in patterns.items() if pattern.search(stripped_line)]
        if len(matches) == 1:
            return matches[0]

    # Fallback for CLIs that print only the conversation text without roles.
    # This intentionally requires exactly one allowed option to avoid matching the brief.
    stripped = strip_ansi(transcript)
    matches = [answer for answer, pattern in patterns.items() if pattern.search(stripped)]
    if len(matches) == 1:
        return matches[0]
    return None


def write_answer_file(path: str | None, payload: dict) -> None:
    if not path:
        return
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def wait_for_answer(
    *,
    before_session_ids: set[str],
    allowed_answers: list[str],
    timeout_seconds: int,
    poll_interval: int,
    answer_file: str | None,
) -> str | None:
    if not allowed_answers:
        return None

    print(
        "\nWaiting for a clear answer from the call transcript "
        f"({', '.join(allowed_answers)})."
    )
    deadline = time.monotonic() + timeout_seconds
    last_seen_sessions: list[str] = []

    while time.monotonic() < deadline:
        logs = capture_vb(["logs"])
        if logs.returncode != 0:
            time.sleep(poll_interval)
            continue

        session_ids = parse_session_ids(logs.stdout)
        new_sessions = [session_id for session_id in session_ids if session_id not in before_session_ids]
        candidates = new_sessions or session_ids[:3]
        last_seen_sessions = candidates

        for session_id in candidates:
            shown = capture_vb(["logs", "show", session_id])
            if shown.returncode != 0:
                continue
            answer = extract_allowed_answer(shown.stdout, allowed_answers)
            if answer:
                payload = {
                    "answer": answer,
                    "session_id": session_id,
                    "source": "vocal_bridge_transcript",
                }
                write_answer_file(answer_file, payload)
                print(f"Detected clear answer from transcript: {answer}")
                print(f"Answer session: {session_id}")
                return answer

        time.sleep(poll_interval)

    write_answer_file(
        answer_file,
        {
            "answer": "",
            "source": "vocal_bridge_transcript",
            "error": "no_clear_answer",
            "sessions_checked": last_seen_sessions,
        },
    )
    print("\nNo clear allowed answer was detected before timeout.")
    return None


def acquire_call_lock():
    CALL_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_file = CALL_LOCK_PATH.open("w", encoding="utf-8")
    fcntl.flock(lock_file, fcntl.LOCK_EX)
    return lock_file


def release_call_lock(lock_file) -> None:
    try:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
    finally:
        lock_file.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Place a Vocal Bridge escalation for a coding-agent decision."
    )
    parser.add_argument("--message", help="Escalation brief text.")
    parser.add_argument("--message-file", help="Path to a file containing the brief.")
    parser.add_argument(
        "--phone",
        help="Phone number to call. Defaults to VOCAL_BRIDGE_ESCALATION_PHONE.",
    )
    parser.add_argument(
        "--transport",
        choices=["phone", "browser"],
        help=(
            "Escalation transport to use. Defaults to "
            "VOCAL_BRIDGE_ESCALATION_TRANSPORT or phone."
        ),
    )
    parser.add_argument(
        "--browser-url",
        help=(
            "Browser voice-session URL. Defaults to "
            "VOCAL_BRIDGE_BROWSER_URL or http://localhost:3000."
        ),
    )
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_FILE),
        help="Env file to load before calling. Defaults to playground/minions/.env.local.",
    )
    parser.add_argument(
        "--set-agent-prompt",
        action="store_true",
        help="Set the live Vocal Bridge agent prompt before calling. This is the default.",
    )
    parser.add_argument(
        "--no-set-agent-prompt",
        action="store_true",
        help="Do not update the live Vocal Bridge agent prompt before calling.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without changing the agent or placing a call.",
    )
    parser.add_argument(
        "--show-logs",
        action="store_true",
        help="Run `vb logs` after placing the call.",
    )
    parser.add_argument(
        "--logs",
        action="store_true",
        help="Load env and run `vb logs` without placing a call.",
    )
    parser.add_argument(
        "--show-session",
        help="Load env and run `vb logs show <session_id>` without placing a call.",
    )
    parser.add_argument(
        "--await-answer",
        action="store_true",
        help="After calling, poll Vocal Bridge logs and extract a clear allowed answer.",
    )
    parser.add_argument(
        "--allowed-answers",
        default="",
        help="Comma-separated exact answers to accept, for example session,json,sqlite,stop.",
    )
    parser.add_argument(
        "--answer-file",
        help="Optional JSON file where the detected answer should be written.",
    )
    parser.add_argument(
        "--answer-timeout",
        type=int,
        default=180,
        help="Seconds to wait for a clear transcript answer with --await-answer.",
    )
    parser.add_argument(
        "--answer-poll-interval",
        type=int,
        default=5,
        help="Seconds between transcript polling attempts with --await-answer.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env_file(Path(args.env_file))

    if args.logs or args.show_session:
        require_vb()
        select_configured_agent()
        if args.logs:
            completed = run_vb(["logs"], check=False)
            return completed.returncode
        completed = run_vb(["logs", "show", args.show_session], check=False)
        return completed.returncode

    brief = read_message(args)
    if not brief:
        raise SystemExit("Escalation brief is empty.")

    transport = (args.transport or os.environ.get("VOCAL_BRIDGE_ESCALATION_TRANSPORT", "phone")).strip().lower()
    if transport not in {"phone", "browser"}:
        raise SystemExit("VOCAL_BRIDGE_ESCALATION_TRANSPORT must be `phone` or `browser`.")

    phone = args.phone or os.environ.get("VOCAL_BRIDGE_ESCALATION_PHONE")
    browser_url = args.browser_url or os.environ.get("VOCAL_BRIDGE_BROWSER_URL", "http://localhost:3000")
    if transport == "phone" and not phone:
        raise SystemExit(
            "Set VOCAL_BRIDGE_ESCALATION_PHONE or pass --phone before calling."
        )
    if transport == "browser":
        browser_url = add_query_param(browser_url, "autostart", "1")

    print("Escalation brief:")
    print(textwrap.indent(brief, "  "))
    if transport == "phone":
        print(f"\nTarget phone: {mask_phone(phone)}")
    else:
        print(f"\nTarget browser session: {browser_url}")

    if args.dry_run:
        print("\nDry run only; no call placed.")
        if not args.no_set_agent_prompt:
            print("Would set the live Vocal Bridge agent prompt before calling.")
        return 0

    require_vb()

    lock_file = acquire_call_lock()
    try:
        if not args.no_set_agent_prompt:
            prompt_text = build_agent_prompt(brief)
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
                handle.write(prompt_text)
                prompt_path = handle.name

            print("\nSetting live Vocal Bridge agent prompt for this escalation.")
            try:
                run_vb(["prompt", "set", "--file", prompt_path])
            finally:
                Path(prompt_path).unlink(missing_ok=True)

        before_session_ids: set[str] = set()
        allowed_answers = parse_allowed_answers(args.allowed_answers)
        if args.await_answer:
            before_logs = capture_vb(["logs"])
            if before_logs.returncode == 0:
                before_session_ids = set(parse_session_ids(before_logs.stdout))

        try:
            select_configured_agent()

            print("\nChecking Vocal Bridge auth status.")
            run_vb(["auth", "status"], check=False)

            if transport == "phone":
                print(f"\nCalling {mask_phone(phone)} with Vocal Bridge.")
                run_vb(["call", phone])
            else:
                open_browser_session(browser_url)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"Vocal Bridge command failed with exit code {exc.returncode}.") from exc

        if args.show_logs:
            print("\nRecent Vocal Bridge logs:")
            run_vb(["logs"], check=False)
        else:
            print(
                "\nCall placed. Use `python3 playground/minions/vocal.py --logs` "
                "and `--show-session <session_id>` for the transcript."
            )

        if args.await_answer:
            wait_for_answer(
                before_session_ids=before_session_ids,
                allowed_answers=allowed_answers,
                timeout_seconds=args.answer_timeout,
                poll_interval=args.answer_poll_interval,
                answer_file=args.answer_file,
            )
    finally:
        release_call_lock(lock_file)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
