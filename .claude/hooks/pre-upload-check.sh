#!/usr/bin/env bash
# PreToolUse hook for Bash. If the command is about to POST to the upload
# webhook, print a quick reachability check first so Claude doesn't waste a
# request on an inactive workflow.
#
# Hook input on stdin: { "tool_name": "Bash", "tool_input": { "command": "..." }, ... }

set -euo pipefail

INPUT=$(cat)
COMMAND=$(python3 -c '
import json, sys
d = json.loads(sys.stdin.read() or "{}")
print(d.get("tool_input", {}).get("command", ""))
' <<<"$INPUT")

# Skip unless this command is hitting the upload webhook.
case "$COMMAND" in
  *"webhook/upload-document"*)
    ;;
  *)
    exit 0
    ;;
esac

# Extract base URL to ping the workflow root for reachability.
URL=$(echo "$COMMAND" | grep -oE 'https?://[^[:space:]"'\'']+/webhook/upload-document' | head -1)
if [ -z "$URL" ]; then
  exit 0
fi

BASE="${URL%/webhook/upload-document}"

# A HEAD on the n8n root is cheap and tells us if n8n is reachable at all.
ROOT_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$BASE/" 2>/dev/null || echo "000")

case "$ROOT_CODE" in
  200) echo "[hook] n8n at $BASE is reachable — proceeding with upload" >&2 ;;
  000) echo "[hook] WARN — n8n at $BASE not reachable (network / DNS / wrong URL)" >&2 ;;
  *)   echo "[hook] WARN — n8n at $BASE returned HTTP $ROOT_CODE on root probe" >&2 ;;
esac

exit 0
