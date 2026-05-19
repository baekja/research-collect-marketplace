#!/usr/bin/env bash
# Block `git add .env` / `git commit` when .env is staged.
# Reads the about-to-run Bash command from stdin (Claude Code hook contract).

set -u
input="$(cat || true)"
cmd="$(printf '%s' "$input" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
    print(d.get("tool_input",{}).get("command",""))
except Exception:
    pass' 2>/dev/null || true)"

# Trigger only for git-related commands
if [[ "$cmd" == *"git add"* || "$cmd" == *"git commit"* ]]; then
  # Is .env staged?
  if git diff --cached --name-only 2>/dev/null | grep -qx '.env'; then
    echo "BLOCKED: .env is staged. Run 'git rm --cached .env' first." >&2
    exit 2   # exit 2 = block in Claude Code hook contract
  fi
fi
exit 0
