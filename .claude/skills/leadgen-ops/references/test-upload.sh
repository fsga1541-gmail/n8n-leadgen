#!/usr/bin/env bash
# Smoke test for the upload webhook. Sends a minimal payload and reports the result.
# Usage:  ./test-upload.sh [N8N_BASE_URL]
# Example: ./test-upload.sh https://n8n.srv923061.hstgr.cloud
#
# If no URL is passed, defaults to localhost:5678.
# Exit code: 0 on HTTP 200, 1 otherwise.

set -euo pipefail

BASE="${1:-http://localhost:5678}"
URL="${BASE%/}/webhook/upload-document"

PAYLOAD=$(cat <<'JSON'
{
  "filename": "smoke-test.txt",
  "kind": "text",
  "content": "Acme Corp is hiring 3 senior engineers based in Singapore. Budget approved for AI training."
}
JSON
)

echo "POST $URL"
HTTP_CODE=$(curl -s -o /tmp/upload_resp.json -w "%{http_code}" \
  -X POST -H "Content-Type: application/json" \
  -d "$PAYLOAD" "$URL")

echo "HTTP $HTTP_CODE"
echo "Body:"
cat /tmp/upload_resp.json
echo

case "$HTTP_CODE" in
  200) echo "OK — webhook accepted the payload."; exit 0 ;;
  404) echo "FAIL — workflow is not active (or the webhook path is wrong)."; exit 1 ;;
  500) echo "FAIL — workflow active but a node errored. Check n8n Executions."; exit 1 ;;
  *)   echo "FAIL — unexpected response."; exit 1 ;;
esac
