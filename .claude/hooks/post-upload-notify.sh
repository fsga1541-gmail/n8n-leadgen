#!/usr/bin/env bash
# PostToolUse hook for Bash. After a webhook upload (or git push), surface a
# concise status line and — on macOS — fire a desktop notification.
#
# Hook input on stdin: full Claude Code tool-use JSON envelope.

set -euo pipefail

INPUT=$(cat)
COMMAND=$(python3 -c '
import json, sys
d = json.loads(sys.stdin.read() or "{}")
print(d.get("tool_input", {}).get("command", ""))
' <<<"$INPUT")

OUTPUT=$(python3 -c '
import json, sys
d = json.loads(sys.stdin.read() or "{}")
r = d.get("tool_response", {}) or {}
if isinstance(r, dict):
    print(r.get("stdout", "") or r.get("output", ""))
else:
    print(r)
' <<<"$INPUT")

notify() {
  local title="$1"
  local body="$2"
  echo "[hook] $title — $body" >&2
  if [[ "$OSTYPE" == "darwin"* ]] && command -v osascript >/dev/null 2>&1; then
    local safe_body
    safe_body=$(printf '%s' "$body" | sed 's/"/\\"/g')
    osascript -e "display notification \"$safe_body\" with title \"$title\"" >/dev/null 2>&1 || true
  fi
}

# Match: webhook upload
if [[ "$COMMAND" == *"webhook/upload-document"* ]]; then
  HTTP_CODE=$(echo "$OUTPUT" | grep -oE 'HTTP/[0-9.]+ [0-9]+' | head -1 | awk '{print $2}')
  if [ -z "$HTTP_CODE" ]; then
    HTTP_CODE=$(echo "$OUTPUT" | grep -oE '"status":[ ]*[0-9]+' | head -1 | grep -oE '[0-9]+')
  fi
  HTTP_CODE=${HTTP_CODE:-unknown}
  case "$HTTP_CODE" in
    200) notify "n8n upload OK" "Webhook accepted the payload" ;;
    404) notify "n8n upload FAILED" "Workflow not active (HTTP 404)" ;;
    500) notify "n8n upload FAILED" "Workflow errored — check Executions panel" ;;
    *)   notify "n8n upload" "HTTP $HTTP_CODE" ;;
  esac
  exit 0
fi

# Match: git push
if [[ "$COMMAND" == *"git push"* ]]; then
  if echo "$OUTPUT" | grep -qE "(rejected|failed|error)"; then
    notify "git push FAILED" "$(echo "$OUTPUT" | tail -1)"
  else
    REPO=$(git -C "${CLAUDE_PROJECT_DIR:-.}" config --get remote.origin.url 2>/dev/null | sed -E 's#.*github.com[:/]([^/]+/[^/.]+).*#\1#' || echo "")
    BRANCH=$(git -C "${CLAUDE_PROJECT_DIR:-.}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
    notify "git push OK" "${REPO:-pushed} → ${BRANCH:-?}"
  fi
  exit 0
fi

exit 0
