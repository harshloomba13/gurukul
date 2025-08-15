#!/usr/bin/env python3
"""
NO-DELETE + PRUNE (strict, PATH-safe) edition: Figma -> Next.js via Claude CLI

- Never deletes anything by default; only overwrites files Claude returns.
- Optional prune_unlisted that removes ONLY previously generated pages (by header).
  * prune_mode="delete" (default) or "archive" to .generated_archive/<timestamp>/
- Strict JSON-only parsing of Claude output: expects [{"path","content"}...].
- Forces the required header line onto every generated page.
- Ensures Nav.tsx and patches layout.tsx.
- PATH-safe: resolves 'claude', 'npm', 'node' and appends common paths.
- doctor() helper for environment checks.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

CONSTRAINT_SYSTEM_PROMPT = (
    "You are a code generation tool. "
    "Your ONLY valid output is a JSON array of files. "
    "Return ONLY: [{\"path\":\"...\",\"content\":\"...\"}, ...]. "
    "No prose. No markdown. No code fences. No intro/outro text. "
    "If uncertain, return []."
)

COMMON_PATHS = [
    "/opt/homebrew/bin",         # Apple Silicon Homebrew
    "/usr/local/bin",            # Intel Homebrew
    os.path.expanduser("~/.local/bin"),
    os.path.expanduser("~/.npm-global/bin"),
    "/usr/bin", "/bin",
]

class ClaudeCodeAutomation:
    def __init__(self, project_path: str = "."):
        self.project_path = str(Path(project_path).resolve())
        cur_path = os.environ.get("PATH", "")
        extras = [p for p in COMMON_PATHS if p and p not in cur_path.split(":")]
        if extras:
            os.environ["PATH"] = cur_path + (":" if cur_path else "") + ":".join(extras)

    # ---------- Binary resolution & shell ----------
    def _resolve_bin(self, exe: str) -> str:
        override = os.environ.get(f"{exe.upper()}_BIN")
        if override and Path(override).exists():
            return override
        found = shutil.which(exe)
        if found:
            return found
        for base in COMMON_PATHS:
            cand = Path(base) / exe
            if cand.exists() and cand.is_file():
                return str(cand)
        raise FileNotFoundError(
            f"Executable not found: '{exe}'. Ensure it is installed and on PATH.\n"
            f"Tried PATH={os.environ.get('PATH')}"
        )

    def _run(self, args: List[str], timeout: int = 1800, capture: bool = True) -> subprocess.CompletedProcess:
        if args and "/" not in args[0]:
            args[0] = self._resolve_bin(args[0])
        print("$", " ".join(shlex.quote(a) for a in args))
        return subprocess.run(args, cwd=self.project_path, capture_output=capture, text=True, timeout=timeout)

    def _sh(self, cmd: str):
        p = self._run(shlex.split(cmd), capture=False)
        if p.returncode != 0:
            raise RuntimeError(f"Command failed: {cmd} (exit={p.returncode})")

    # ---------- Figma URL helpers ----------
    _KEY_RE = re.compile(
        r"https?://(?:www\\.)?figma\\.com/(?:file|design|proto|presentation|embed|board)/([A-Za-z0-9]{22,64})"
    )

    def _file_key(self, url: str) -> str:
        m = self._KEY_RE.match(url or "")
        return m.group(1) if m else "unknown"

    def _node_id(self, url: str) -> str:
        from urllib.parse import urlparse, parse_qs
        try:
            q = parse_qs(urlparse(url).query)
            return q.get("node-id", ["ROOT"])[0]
        except Exception:
            return "ROOT"

    # ---------- Paths ----------
    def _route_to_path(self, route: str) -> Path:
        if route == "/":
            return Path(self.project_path) / "src" / "app" / "page.tsx"
        segs = [s for s in route.split("/") if s]
        return Path(self.project_path) / "src" / "app" / Path(*segs) / "page.tsx"

    # ---------- Build ----------
    def _rebuild(self):
        self._sh("npm install")
        self._sh("npm run build")

    # ---------- Writing & checks ----------
    def _write_file_blobs(self, blobs: List[Dict[str, str]]):
        count = 0
        for f in blobs:
            path = f.get("path")
            content = f.get("content")
            if not path or content is None:
                continue
            full = Path(self.project_path) / path if not str(path).startswith(self.project_path) else Path(path)
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            count += 1
        print(f"✅ Wrote {count} files")

    def _assert_headers(self, figma_pages: List[Dict[str, str]]):
        missing, bad = [], []
        for p in figma_pages:
            fp = self._route_to_path(p["route"])
            if not fp.exists():
                missing.append(str(fp)); continue
            text = fp.read_text(encoding="utf-8")
            expect_key = self._file_key(p["url"])
            expect_node = self._node_id(p["url"])
            needed = f"// GENERATED_FROM_FIGMA_KEY: {expect_key} NODE_ID: {expect_node} ROUTE: {p['route']}"
            if not text.startswith(needed):
                bad.append(str(fp))
        return missing, bad

    def _ensure_nav_component(self, figma_pages: List[Dict[str, str]]):
        comp_dir = Path(self.project_path) / "src" / "app" / "_components"
        comp_dir.mkdir(parents=True, exist_ok=True)
        links = []
        for p in figma_pages:
            label = (p.get("name") or p["route"].strip("/") or "home")
            links.append(f'        <Link href="{p["route"]}" className="px-3 py-2 rounded hover:bg-gray-100">{label}</Link>')
        nav_tsx = """import Link from "next/link";

export default function Nav() {
  return (
    <nav className="w-full border-b bg-white/70 backdrop-blur sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 h-12 flex items-center gap-2">
{links}
      </div>
    </nav>
  );
}
""".replace("{links}", "\n".join(links))
        (comp_dir / "Nav.tsx").write_text(nav_tsx, encoding="utf-8")

        layout = Path(self.project_path) / "src" / "app" / "layout.tsx"
        if layout.exists():
            text = layout.read_text(encoding="utf-8")
            if 'from "@/app/_components/Nav"' not in text:
                text = text.replace('import "./globals.css";', 'import "./globals.css";\nimport Nav from "@/app/_components/Nav";')
            if "<Nav " not in text and "<Nav/>" not in text and "<Nav />" not in text:
                text = text.replace("{children}", "<Nav />\n        {children}")
            layout.write_text(text, encoding="utf-8")

    # ---------- FORCE header after write ----------
    def _force_header(self, route: str, url: str):
        fp = self._route_to_path(route)
        if not fp.exists():
            return
        text = fp.read_text(encoding="utf-8")
        header = f"// GENERATED_FROM_FIGMA_KEY: {self._file_key(url)} NODE_ID: {self._node_id(url)} ROUTE: {route}\n"
        if not text.startswith(header):
            fp.write_text(header + text, encoding="utf-8")
            print(f"🔧 Preprended header to {fp}")

    # ---------- PRUNE previously generated pages ----------
    def _prune_generated_pages(self, keep_routes: List[str], mode: str = "delete") -> None:
        """
        Remove ONLY pages we generated (recognized by header), except those in keep_routes.
        mode: "delete" (default) or "archive" to .generated_archive/<timestamp>/
        """
        from time import strftime
        app_dir = Path(self.project_path) / "src" / "app"
        removed = []

        def is_generated(fp: Path) -> bool:
            try:
                first = fp.read_text(encoding="utf-8").splitlines()[0]
            except Exception:
                return False
            return first.startswith("// GENERATED_FROM_FIGMA_KEY:")

        archive_root = None
        if mode == "archive":
            archive_root = Path(self.project_path) / ".generated_archive" / strftime("%Y%m%d-%H%M%S")

        # root "/"
        root_page = app_dir / "page.tsx"
        if root_page.exists() and is_generated(root_page) and ("/" not in keep_routes):
            if mode == "archive":
                dst = archive_root / "root" / "page.tsx"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(root_page), str(dst))
            else:
                root_page.unlink()
            removed.append("/")

        # subroutes
        for d in app_dir.iterdir():
            if not d.is_dir():
                continue
            if d.name.startswith("_") or d.name in {"api", "fonts"}:
                continue
            page_file = d / "page.tsx"
            if not page_file.exists() or not is_generated(page_file):
                continue
            route = "/" + d.name
            if route in keep_routes:
                continue
            if mode == "archive":
                dst = archive_root / d.name / "page.tsx"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(page_file), str(dst))
            else:
                page_file.unlink()
            try:
                if not any(d.iterdir()):
                    d.rmdir()
            except Exception:
                pass
            removed.append(route)

        if removed:
            if mode == "archive":
                print(f"🧹 Archived generated pages not in keep list: {removed}")
            else:
                print(f"🧹 Pruned generated pages not in keep list: {removed}")
        else:
            print("🧹 Nothing to prune (no generated pages outside keep list).")

    # ---------- Claude headless call ----------
    def _claude_print(self, prompt: str, timeout: int = 900) -> Optional[str]:
        print("=" * 60)
        print("Claude (print) prompt (first 320 chars):")
        print(prompt[:320] + ("..." if len(prompt) > 320 else ""))
        print("=" * 60)

        args = [
            "claude",
            "-p", prompt,
            "--append-system-prompt", CONSTRAINT_SYSTEM_PROMPT,
            "--output-format", "text",
            "--verbose",
            "--disallowedTools", "Bash,Edit,Read,WebSearch",
        ]
        try:
            result = self._run(args, timeout=timeout, capture=True)
        except FileNotFoundError as e:
            print("❌", e)
            return None

        print("Return code:", result.returncode)
        if result.stderr:
            print("STDERR:\n", result.stderr[:2000])
        print("STDOUT (first 600 chars):\n", (result.stdout or "")[:600])
        if result.returncode != 0:
            return None
        return result.stdout or ""

    # ---------- Prompt builder ----------
    def build_json_prompt(self, figma_pages: List[Dict[str, str]]) -> str:
        pages_block = "\n".join([f"- {p['route']}: {p['url']}" for p in figma_pages])
        resolved_keys = "\n".join([f"{p['route']} :: {self._file_key(p['url'])}" for p in figma_pages])
        resolved_nodes = "\n".join([f"{p['route']} :: {self._node_id(p['url'])}" for p in figma_pages])

        return f"""
Generate files for a Next.js 13+ App Router project **from the following Figma pages**.

PAGES (route → URL):
{pages_block}

REQUIREMENTS:
1) For each route, create the page file (app router):
   "/"      → src/app/page.tsx
   "/foo"   → src/app/foo/page.tsx
2) The FIRST line of every page MUST be exactly:
   // GENERATED_FROM_FIGMA_KEY: <FILE_KEY> NODE_ID: <NODE_ID> ROUTE: <ROUTE>
3) Each page MUST reflect its own Figma design. Do NOT reuse content between routes.
4) Use Tailwind for styling. If charts appear, use Recharts with placeholder data.
5) RESPONSE FORMAT (STRICT):
   Return ONLY a JSON array of objects: [{{"path":"...","content":"..."}}, ...]
   - Start with '[' and end with ']'
   - No prose. No markdown. No backticks. No prefaces.
   - If uncertain, return an empty array []

RESOLVED_KEYS (use these verbatim in the first line of each page):
{resolved_keys}

RESOLVED_NODE_IDS:
{resolved_nodes}
""".strip()

    # ---------- Strict JSON extractor ----------
    def _extract_json_array(self, text: str) -> Optional[List[Dict[str, str]]]:
        import json, re

        def parse_candidate(s: str) -> Optional[List[Dict[str, str]]]:
            try:
                arr = json.loads(s)
                if isinstance(arr, list):
                    clean = []
                    for x in arr:
                        if isinstance(x, dict) and isinstance(x.get("path"), str) and isinstance(x.get("content"), str):
                            clean.append({"path": x["path"], "content": x["content"]})
                    if clean and len(clean) == len(arr):
                        return clean
            except Exception:
                pass
            return None

        m = re.search(r"```(?:json)?\s*(\[\s*.*?\s*\])\s*```", text, re.S | re.I)
        if m:
            val = parse_candidate(m.group(1))
            if val is not None:
                return val

        start, end = text.find("["), text.rfind("]")
        if start != -1 and end != -1 and end > start:
            frag = text[start:end+1]
            val = parse_candidate(frag)
            if val is not None:
                return val

        return None

    # ---------- Diagnostics ----------
    def doctor(self) -> None:
        root = Path(self.project_path)
        print("Project path:", root)
        print("Exists:", root.exists())
        pkg = root / "package.json"
        print("package.json:", "OK" if pkg.exists() else "MISSING")
        appdir = root / "src" / "app"
        print("src/app:", "OK" if appdir.exists() else "MISSING")
        for exe in ("claude", "npm", "node"):
            try:
                resolved = self._resolve_bin(exe)
                print(f"{exe}: OK → {resolved}")
            except FileNotFoundError:
                print(f"{exe}: NOT FOUND")
        layout = appdir / "layout.tsx"
        print("layout.tsx:", "OK" if layout.exists() else "MISSING (not fatal)")
        print("PATH:", os.environ.get("PATH"))

    # ---------- Public API ----------
    def generate_app_from_figma(self, figma_url: str) -> bool:
        if not figma_url:
            print("No figma_url provided")
            return False
        return self.generate_multi_page_app([{"url": figma_url, "name": "home", "route": "/"}])

    def generate_multi_page_app(self, figma_pages: List[Dict[str, str]], prune_unlisted: bool = False, prune_mode: str = "delete") -> bool:
        print("Starting Figma -> Next.js generation (NO-DELETE + PRUNE)…")
        print("Routes:", [p["route"] for p in figma_pages])
        print("Safety: By default no deletion; pruning only touches pages we generated (header-marked).")

        contract = self.build_json_prompt(figma_pages)
        attempts = 0
        blobs: Optional[List[Dict[str, str]]] = None

        while attempts < 3 and blobs is None:
            attempts += 1
            attempt_prompt = contract if attempts == 1 else (
                contract + "\\n\\nFORMAT ENFORCEMENT:\\n"
                "Re-output ONLY the JSON array of files for the same task.\\n"
                "Start with '[' and end with ']'. No other text."
            )
            out = self._claude_print(attempt_prompt, timeout=900)

        #     if not out:
        #         print(f"Attempt {attempts}: no output from Claude.")
        #         continue

            blobs = self._extract_json_array(out or "")
            if blobs is None:
                print(f"Attempt {attempts}: output was not valid JSON; will re-ask.")

        if blobs is None:
            print("❌ Failed to obtain JSON files from Claude after 3 attempts.")
            return False

        # 2) Write files
        try:
            self._write_file_blobs(blobs)
        except Exception as e:
            print("❌ Failed to write files:", e); return False

        # 3) Force header for each target route
        try:
            for p in figma_pages:
                self._force_header(p["route"], p["url"])
        except Exception as e:
            print("⚠️ Could not force headers:", e)

        # 4) Ensure Nav and patch layout
        try:
            self._ensure_nav_component(figma_pages)
            print("✅ Nav ensured and layout patched")
        except Exception as e:
            print("⚠️ Could not ensure Nav/layout:", e)

        # 5) Optional prune
        if prune_unlisted:
            keep = [p["route"] for p in figma_pages]
            self._prune_generated_pages(keep_routes=keep, mode=prune_mode)

        # 6) Verify header markers present per route
        missing, bad = self._assert_headers(figma_pages)
        if missing:
            print("❌ Missing page files:", missing); return False
        if bad:
            print("❌ Pages missing/incorrect header markers:", bad); return False
        print("✅ Header markers OK")

        # 7) Build project
        try:
            self._rebuild()
            print("✅ Build OK")
        except Exception as e:
            print("❌ Build failed:", e); return False

        print("🎉 Generation complete")
        return True