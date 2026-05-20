#!/usr/bin/env python
"""Block `git add .env` / `git commit` when .env is staged.

Reads the Claude Code PreToolUse payload (JSON) from stdin, inspects the
about-to-run Bash command, and exits 2 to block when `.env` is in the index.
Cross-platform replacement for the original check_env.sh.
"""
import json
import subprocess
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    cmd = payload.get("tool_input", {}).get("command", "")
    if "git add" not in cmd and "git commit" not in cmd:
        return 0

    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return 0

    staged = proc.stdout.splitlines()
    if ".env" in staged:
        sys.stderr.write(
            "BLOCKED: .env is staged. Run 'git rm --cached .env' first.\n"
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
