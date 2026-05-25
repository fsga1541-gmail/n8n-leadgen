#!/usr/bin/env bash
# PostToolUse hook for Edit / Write tool calls.
# When the file just touched is the n8n workflow JSON, verify it still parses.
# If it doesn't parse, print a loud warning to stderr — Claude will see it and
# can self-correct on the next turn.
#
# Hook input on stdin (Claude Code format):
#   { "tool_name": "Edit", "tool_input": { "file_path": "...", ... }, ... }

set -euo pipefail

INPUT=$(cat)

# Extract tool_name and file_path with python (always available; jq might not be).
read -r TOOL_NAME FILE_PATH <<<"$(python3 -c '
import json, sys
d = json.loads(sys.stdin.read() or "{}")
print(d.get("tool_name", ""), d.get("tool_input", {}).get("file_path", ""))
' <<<"$INPUT")"

# Only act when the workflow JSON was edited.
case "$FILE_PATH" in
  *"Lead Qualification Agent with RAG and Telegram interface.json")
    ;;
  *)
    exit 0
    ;;
esac

if python3 -c "import json; json.load(open('$FILE_PATH'))" 2>/dev/null; then
  echo "[hook] workflow JSON parses" >&2
  exit 0
else
  echo "[hook] WORKFLOW JSON IS BROKEN — last edit produced invalid JSON" >&2
  python3 -c "import json; json.load(open('$FILE_PATH'))" 2>&1 | tail -5 >&2
  # Exit 1 (not 2): warn loudly but don't block. Claude sees the stderr and can fix.
  exit 1
fi
