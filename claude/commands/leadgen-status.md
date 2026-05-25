---
description: Run an end-to-end health check of the lead-generation stack (web tool, n8n webhook, Supabase, Telegram bot). Useful when "the bot doesn't respond" or "the upload fails" — it pinpoints which layer is broken.
---

You are diagnosing the lead-generation pipeline for this project. Run the checks below in parallel where possible, then write a single concise verdict for the user.

# Read the configuration

Read these without printing them back:
- `.env` for `N8N_API_URL`, `N8N_API_KEY`, `TELEGRAM_BOT_TOKEN`, `NEXT_PUBLIC_SUPABASE_URL`
- `Lead Qualification Agent with RAG and Telegram interface.json` to confirm the webhook path is `upload-document` and the insert-side Supabase Vector Store has `tableName: documents`

# Health checks

Run these in parallel via Bash:

1. **Web tool reachable?** `curl -s -o /dev/null -w "%{http_code}" http://localhost:8889/` — expect 200. If non-200, tell the user to run `cd web && python3 -m http.server 8889`.

2. **n8n reachable?** `curl -s -o /dev/null -w "%{http_code}" $N8N_API_URL/../` — expect 200.

3. **Upload webhook registered?** `curl -s -X POST -H "Content-Type: application/json" -d '{"filename":"healthcheck.txt","content":"ping"}' "$N8N_BASE/webhook/upload-document" -w "\n%{http_code}"` (where `$N8N_BASE` is `N8N_API_URL` with `/api/v1` stripped). Interpret:
   - 200 → webhook is live and the workflow ran
   - 404 → workflow isn't active
   - 500 → workflow active but errored — tell user to check n8n Executions panel

4. **Telegram bot wired up?** `curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"` — interpret:
   - `url` empty → bot has no webhook (workflow not active)
   - `url` matches expected n8n URL + `pending_update_count == 0` → healthy
   - `pending_update_count > 0` → n8n returning errors, check Executions

5. **Supabase docs count.** If the supabase MCP is authenticated, run a quick `select count(*) from documents` against the project pointed to by `NEXT_PUBLIC_SUPABASE_URL`. Otherwise skip and note that the user can verify in Supabase → Table Editor.

# Output

Produce a single Markdown table:

| Check | Status | Detail |
|---|---|---|
| Web tool (8889) | ✅ / ❌ | … |
| n8n reachable | ✅ / ❌ | … |
| Upload webhook | ✅ / ❌ | HTTP code, hint |
| Telegram webhook | ✅ / ❌ | url + pending count |
| Supabase `documents` rows | ✅ / ❌ | count or "skipped" |

Then a one-line verdict ("Everything green — try uploading a file." or "❌ Telegram bot has no webhook — activate the n8n workflow.") and, if anything failed, the single most useful next action.

Do not echo any token, key, or service-role secret in the output.
