---
name: leadgen-ops
description: Operational playbook for THIS project — the lead-qualification n8n workflow + Supabase pgvector + Telegram bot + static web uploader. Use this skill any time the user asks to deploy, set up, activate, debug, or fix anything in the lead-generation pipeline. Knows the specific failure modes (empty tableName silently 500-ing the webhook, Default Data Loader needing expressionData mode, the Code node dropping empty Telegram replies, OpenAI 429s, Supabase service_role vs publishable key confusion). Skip this skill for generic n8n / Supabase / OpenAI questions — only use it for THIS workflow.
---

You are operating on the project at the repo root: a four-component stack consisting of a static HTML/CSS/JS uploader (`web/`), an n8n workflow JSON (`Lead Qualification Agent with RAG and Telegram interface.json`), a Supabase Postgres database with `pgvector`, and a Telegram bot. The pipeline ingests CSV/Excel/Text files into a `documents` vector table, then answers questions about that knowledge base via Telegram while scoring users as leads from 0–100.

This skill compresses the lessons learned setting this stack up so future runs don't repeat the same hour of debugging.

## Decision tree — what to do based on user intent

| User says… | Do this |
|---|---|
| "set up", "deploy", "import", "activate" | See [§Deploying from scratch](#deploying-from-scratch) |
| "bot not responding", "upload fails", "doesn't work" | See [§Debugging](#debugging) |
| "add documents table", "set up supabase" | Run the SQL in [references/supabase-schema.sql](references/supabase-schema.sql) |
| "wire credentials", "fix missing creds" | See [§Wiring credentials via the n8n API](#wiring-credentials-via-the-n8n-api) |
| "secure the webhook", "add auth" | See [§Hardening the upload webhook](#hardening-the-upload-webhook) |
| "test upload", "send a sample" | See [references/test-upload.sh](references/test-upload.sh) |

## Critical project-specific facts

These are the bugs that cost the most time when this project was first deployed. Memorize them:

1. **The insert-side `Supabase Vector Store` node MUST have `tableName.value: "documents"`.** When this is empty (default after import), the webhook returns 500 with no useful error, and the Default Data Loader's expression silently fails. Always grep the JSON for `"tableName"` and confirm both Vector Store nodes (insert and retrieve-as-tool) have `value: "documents"`.

2. **The `Default Data Loader` MUST use `jsonMode: "expressionData"`** with `jsonData: "={{ $('Upload Webhook').item.json.body.content }}"`. With the default `allInputData` mode, the loader stringifies the entire webhook payload (including `headers`, `query`, etc.) and embeds that — completely useless for RAG. The `match_documents` query will return rows but they'll be JSON-shaped junk.

3. **The Supabase credential `Host` is the *Supabase project URL*, NOT the n8n instance URL.** Users frequently paste the n8n cloud URL here. Correct value: `https://<projectref>.supabase.co`.

4. **The `Service Role Secret` is the legacy `service_role` JWT** (starts with `eyJhbGc...`). NOT the `anon` key, NOT the `sb_publishable_*` key, NOT the `sb_secret_*` key, NOT the personal access token (`sbp_*`). The new Supabase API Keys UI hides the legacy JWT — scroll for "Legacy JWT keys" or "JWT Settings".

5. **`Send a text message` (Telegram reply) needs the same Telegram credential as the trigger.** Easy to miss because most attention goes to the trigger node. If this is unset, the workflow runs to completion and returns 200 to Telegram, but no reply is sent — making it look like the bot is broken when actually only the reply step is.

6. **Telegram silently drops empty messages.** The Code-in-JavaScript node parses the AI Agent's output as JSON; if parsing fails, `reply_to_user` is `""` — and the user sees nothing. Always confirm AI Agent output is valid JSON before blaming the Telegram node.

7. **n8n's public API `PUT /workflows/{id}` only accepts `name`, `nodes`, `connections`, `settings`, `staticData`** — and `settings` only allows `executionOrder`. Stripping other keys is mandatory. Activation via `POST /workflows/{id}/activate` is unreliable; flipping the toggle in the n8n UI is more dependable.

8. **Disabled nodes still need credentials for activation** — except `Send a message` (Gmail), which can be flagged `"disabled": true` in the JSON to skip the credential check. If a Gmail credential isn't available, set this flag before activating, otherwise n8n refuses with "Missing required credential: gmailOAuth2".

9. **Telegram only allows ONE webhook URL per bot.** If the bot was previously wired to a different n8n instance (e.g. localhost), activating in a new instance just replaces it. Use `getWebhookInfo` to confirm where the bot currently delivers updates.

10. **Cloud n8n at `n8n.srv923061.hstgr.cloud` is the published instance for this project.** The static web tool defaults to `https://n8n.srv923061.hstgr.cloud/webhook/upload-document`. If the user is on a different instance, they need to update the URL in the form (it persists in `localStorage` under `lq_webhook_url`).

## Deploying from scratch

End-to-end deploy procedure for a fresh n8n + Supabase + bot setup. Each step has an explicit success check — don't proceed if a check fails.

### 1. Supabase

```bash
# Open the SQL Editor for the project, paste references/supabase-schema.sql, run.
# Verify:
#   Table Editor → public → documents exists with columns: id, content, metadata, embedding
```

### 2. Credentials — collect once, never paste into source

| Service | Field | Where to find |
|---|---|---|
| Supabase | Project URL | Supabase dashboard → top of project page |
| Supabase | `service_role` JWT | Settings → API Keys → Legacy JWT keys → service_role |
| OpenAI | API key | platform.openai.com/api-keys (`sk-...`) |
| Telegram | Bot token | BotFather `/newbot` reply |

### 3. n8n credentials

In n8n → Credentials → New, create one of each:
- **Supabase API** (host + service-role secret)
- **OpenAI** (API key)
- **Telegram** (bot token)
- **Gmail OAuth2** — optional. Skip if not using sales notification.

### 4. Import the workflow

In n8n → Workflows → Import from File → select [Lead Qualification Agent with RAG and Telegram interface.json](Lead%20Qualification%20Agent%20with%20RAG%20and%20Telegram%20interface.json).

### 5. Wire credentials

For every node listed below, open and pick the right credential from the dropdown. **The two columns marked ⚠️ are the easy-to-miss ones:**

| Node | Credential type | Notes |
|---|---|---|
| OpenAI Chat Model | OpenAI | |
| Embeddings OpenAI | OpenAI | (insert side) |
| Embeddings OpenAI1 | OpenAI | ⚠️ (retrieve side) |
| Supabase Vector Store | Supabase | Operation = Insert Documents, Table = `documents` |
| Supabase Vector Store1 | Supabase | ⚠️ Operation = Retrieve as Tool, Table = `documents` |
| Telegram Trigger | Telegram | |
| Send a text message | Telegram | ⚠️ Often missed |
| Send a message (Gmail) | Gmail | Or right-click → **Disable** if no Gmail credential |

For automation, see [§Wiring credentials via the n8n API](#wiring-credentials-via-the-n8n-api).

### 6. Activate

Toggle **Active** in the top-right of the editor. n8n will list any remaining cred issues — fix and retry.

### 7. Verify

```bash
# Upload webhook reachable
curl -i -X POST -H "Content-Type: application/json" \
  -d '{"filename":"healthcheck.txt","content":"hello world"}' \
  <N8N_BASE>/webhook/upload-document
# Expect: HTTP 200, body { ok: true, ... }

# Telegram bot wired up
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | python3 -m json.tool
# Expect: url matches the n8n instance, pending_update_count == 0
```

## Wiring credentials via the n8n API

When the user has many nodes to wire and the credentials already exist by name, automate it.

```bash
API_KEY="$N8N_API_KEY"
BASE="$N8N_API_URL"
WF_ID="<workflow id>"

# 1. Fetch the workflow
curl -sS "$BASE/workflows/$WF_ID" -H "X-N8N-API-KEY: $API_KEY" > /tmp/wf.json

# 2. Edit nodes in Python — only allowed top-level keys: name/nodes/connections/settings/staticData
python3 <<'PY'
import json
with open('/tmp/wf.json') as f: wf = json.load(f)
allowed = {k: wf[k] for k in ('name','nodes','connections','settings','staticData') if k in wf}
allowed['settings'] = {'executionOrder': allowed.get('settings', {}).get('executionOrder', 'v1')}

CREDS = {
    'openAiApi':    {'id': '<oai-cred-id>', 'name': 'OpenAI account'},
    'supabaseApi':  {'id': '<sb-cred-id>',  'name': 'Supabase account'},
    'telegramApi':  {'id': '<tg-cred-id>',  'name': 'Telegram account'},
}
for n in allowed['nodes']:
    t = n.get('type', '')
    creds = n.setdefault('credentials', {})
    if t in ('@n8n/n8n-nodes-langchain.lmChatOpenAi','@n8n/n8n-nodes-langchain.embeddingsOpenAi'):
        creds['openAiApi'] = CREDS['openAiApi']
    elif t == '@n8n/n8n-nodes-langchain.vectorStoreSupabase':
        creds['supabaseApi'] = CREDS['supabaseApi']
    elif t in ('n8n-nodes-base.telegramTrigger','n8n-nodes-base.telegram'):
        creds['telegramApi'] = CREDS['telegramApi']
    if t == 'n8n-nodes-base.gmail':
        n['disabled'] = True   # skip Gmail unless OAuth credential is available

with open('/tmp/wf.out','w') as f: json.dump(allowed, f)
PY

# 3. PUT it back
curl -sS -X PUT "$BASE/workflows/$WF_ID" \
  -H "X-N8N-API-KEY: $API_KEY" -H "Content-Type: application/json" \
  --data @/tmp/wf.out
```

To list available credentials by name: `curl -sS "$BASE/credentials" -H "X-N8N-API-KEY: $API_KEY"`.

## Debugging

Run these in order. Stop at the first failing layer.

### Layer 1: web tool

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8889/
# 200 → fine. anything else → "cd web && python3 -m http.server 8889" not running.
```

### Layer 2: upload webhook

```bash
curl -i -X POST -H "Content-Type: application/json" \
  -d '{"filename":"x.txt","content":"y"}' \
  <N8N_BASE>/webhook/upload-document
```

| HTTP code | Meaning | Fix |
|---|---|---|
| 404 | Workflow not active | Toggle on in n8n UI |
| 500 | Workflow active but a node failed | Open n8n Executions panel, find the red node |
| 200 | Webhook works end-to-end | Move to layer 3 |
| Failed to fetch (browser only) | CORS preflight failing because the workflow returned a non-200 to OPTIONS | Almost always the same as 500 above — the underlying execution is broken |

### Layer 3: Telegram

```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" | python3 -m json.tool
```

- `url` empty → workflow not active.
- `url` points to a different n8n instance → that bot was wired elsewhere; reactivate this workflow to claim the webhook.
- `pending_update_count > 0` → n8n is rejecting deliveries. Open Executions.
- `pending_update_count == 0` AND bot still doesn't reply → the workflow ran but the reply was empty. Most common causes:
  - `Send a text message` node missing Telegram credential.
  - AI Agent failed (OpenAI 429, no quota, wrong model).
  - AI Agent returned non-JSON; Code node defaulted `reply_to_user` to `""`.

### Layer 4: Supabase

```bash
# Via the Supabase MCP server (preferred):
#   list_tables on the project, confirm `documents` exists.
#   execute_sql: select count(*) from documents;
# Or via the dashboard → Table Editor → documents.
```

If `documents` count is 0 after a successful upload, the Default Data Loader expression is wrong (see Critical Fact #2).

## Hardening the upload webhook

The webhook is unauthenticated by default. For any deployment past local dev:

1. **Origin restriction.** In the Webhook node options, set `allowedOrigins` to your specific Pages URL (e.g. `https://alfredang.github.io`) instead of `*`.
2. **Header auth.** Add a Code node at the top of the upload branch:
   ```js
   const expected = $env.UPLOAD_TOKEN; // configured in n8n env
   const got = $input.item.json.headers['x-upload-token'];
   if (!expected || got !== expected) {
     throw new Error('Unauthorized');
   }
   return $input.all();
   ```
   Then update the web tool to send `x-upload-token` in the fetch headers (read from a config field, NOT hardcoded).
3. **Reverse proxy.** Front the webhook with a service that adds basic auth or signed-request validation.

Don't rely on obscurity (the URL is in the public Pages-hosted HTML).

## What this skill does NOT cover

- Generic n8n questions (use built-in n8n knowledge or n8n MCP tools).
- Generic Supabase / Postgres optimisation (use the supabase skill if available globally).
- Brand-new workflows or unrelated automation. This skill is *only* for the lead-generation stack in this repo.
