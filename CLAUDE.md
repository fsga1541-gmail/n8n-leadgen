# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project shape

Two artifacts that work together; there is no build step or package manager.

1. **`Lead Qualification Agent with RAG and Telegram interface.json`** — an exported n8n workflow. The source of truth lives in the n8n instance (cloud at `n8n.srv923061.hstgr.cloud` or local at `localhost:5678`); this JSON is the importable / re-importable copy. After editing it locally, the user re-imports into n8n via **Workflows → Import from File**.
2. **`web/`** — a static HTML/CSS/JS uploader. No bundler. Excel parsing is via SheetJS loaded from a CDN in `index.html`. Run with `python3 -m http.server <port>` from inside `web/`.

`.mcp.json` wires up two MCP servers (`n8n-mcp`, `supabase`). Both read tokens from `.env` (`SUPABASE_ACCESS_TOKEN`, `N8N_API_URL`, `N8N_API_KEY`). If MCP calls return Unauthorized, the server is reading from MCP config — not project `.env` — so the env vars need to be exported before the Claude Code session starts.

## How the two pieces connect

```
Browser (web/index.html)
  └── parses CSV/Excel/Text in-browser → POST { filename, kind, content }
       │
       ▼
n8n  Webhook (/webhook/upload-document, CORS *)
  └── → Supabase Vector Store (mode: insert, table: documents)
        ← Default Data Loader (jsonMode: expressionData → $('Upload Webhook').item.json.body.content)
        ← Embeddings OpenAI
  └── → Respond to Webhook

n8n  Telegram Trigger
  └── → AI Agent (system prompt: 2-stage flow — register name+email, then RAG-answer)
        ← Google Gemini Chat Model (credential type: googlePalmApi)
        ← Simple Memory (sessionKey = telegram user id, window = 10)
        ← Supabase Vector Store1 (mode: retrieve-as-tool, same `documents` table)
              ← Embeddings OpenAI1
  └── → Code in JavaScript (strips ```json fences, parses output, surfaces Name/Email/lead_score; falls back to a friendly reply if the agent emits non-JSON so Telegram never receives an empty `text`)
  └── → If (lead_score > 69)
        ├── true → Send a message (Gmail — disabled by default until OAuth credential exists; recipient is a `sales@sales.com` placeholder, replace before activation)
        └── false → Send a text message (Telegram reply via $('Telegram Trigger').item.json.message.chat.id)
```

The Default Data Loader **must** use `jsonMode: expressionData` pulling `$('Upload Webhook').item.json.body.content`. With the default `allInputData` mode it would JSON.stringify the entire webhook payload and embed that — useless for RAG.

## Required external state

The workflow assumes this Supabase schema exists in the project the credential points at. Without it, the Vector Store nodes will silently 500 the webhook. Create with the SQL Editor:

```sql
create extension if not exists vector;
create table if not exists documents (
  id bigserial primary key,
  content text,
  metadata jsonb,
  embedding vector(1536)
);
create index if not exists documents_embedding_idx
  on documents using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create or replace function match_documents (
  query_embedding vector(1536), match_count int default 5, filter jsonb default '{}'
) returns table (id bigint, content text, metadata jsonb, similarity float)
language plpgsql as $$ begin
  return query select documents.id, documents.content, documents.metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
    from documents where documents.metadata @> filter
    order by documents.embedding <=> query_embedding limit match_count;
end; $$;
```

Required n8n credentials (the IDs in the JSON are placeholders from the original exporter — they always need to be re-picked on import):
- `supabaseApi` — **Host** = the Supabase project URL (e.g. `https://jbhhthtkdjtkbxmtpdvp.supabase.co`); **Service Role Secret** = the legacy `service_role` JWT (NOT the new `sb_publishable_*` / `sb_secret_*` keys, NOT the anon key).
- `googlePalmApi` — applied to the **Google Gemini Chat Model** node. Get an API key from https://aistudio.google.com/app/apikey.
- `openAiApi` — applied to both Embeddings OpenAI nodes (insert side **and** retrieve side). The chat model is Gemini, not OpenAI.
- `telegramApi` — applied to Telegram Trigger AND Send a text message (easy to forget the second one).
- `gmailOAuth2` — optional. If absent, **disable the `Send a message` (Gmail) node** before activating, otherwise n8n refuses activation citing missing credentials. The `sendTo` field is hardcoded to a `sales@sales.com` placeholder — replace it before going live.

## Common tasks

```bash
# Serve the uploader (default port the user has been using)
cd web && python3 -m http.server 8889

# Validate workflow JSON parses after edits
python3 -c "import json; json.load(open('Lead Qualification Agent with RAG and Telegram interface.json'))"

# Probe whether a webhook is registered (returns 404 if workflow inactive)
curl -i -X POST -H 'Content-Type: application/json' \
  -d '{"filename":"t.txt","content":"hello"}' \
  http://localhost:5678/webhook/upload-document

# Inspect the Telegram bot's webhook binding (debug "bot not responding")
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | python3 -m json.tool

# List active workflows on local n8n via the public API
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_API_URL/workflows?active=true&limit=50" | python3 -m json.tool
```

## Editing the workflow JSON

The user routinely edits the exported JSON and re-imports. Two gotchas:

1. **Webhook path is hardcoded** to `upload-document` and the web tool defaults to that path. If you rename it, also update [web/index.html](web/index.html) (the `value` and `placeholder` on `#webhookUrl`).
2. **n8n's public API `PUT /workflows/{id}` only accepts `name`, `nodes`, `connections`, `settings`, `staticData`** — and `settings` only allows `executionOrder`. Stripping other keys (`id`, `versionId`, `meta`, `tags`, `active`, etc.) is required or the request 400s with `must NOT have additional properties`. Activation via the public API (`POST /workflows/{id}/activate`) is unreliable — it is more dependable to flip the toggle in the n8n editor UI.

## Web tool details worth knowing

- The webhook URL field persists in `localStorage` under key `lq_webhook_url`. After updating the default in `index.html`, existing browsers keep the old value until the user clears it (`localStorage.removeItem('lq_webhook_url')`) or pastes a new URL.
- File parsing happens entirely client-side. CSV/TSV/TXT use `FileReader.readAsText`; XLS/XLSX use `XLSX.read` and concatenate sheets as `# Sheet: <name>\n<csv>`.
- The webhook is called as JSON `{ filename, kind, content }`. Don't change to multipart unless you also change the Default Data Loader's expression.

## When the Telegram bot "doesn't respond"

The most useful single check is `getWebhookInfo` against the bot token. If `pending_update_count` is 0 and `url` matches the active n8n instance, Telegram is delivering messages and getting HTTP 200 back — the bug is inside the workflow (almost always either a Gemini quota / 429 on the AI Agent, an OpenAI 429 on the Embeddings node, or the Code node receiving non-JSON output. The Code node now substitutes a fallback string when JSON parsing fails so Telegram doesn't 400 on an empty `text`, but a legitimate node failure upstream will still error the run). Open the n8n Executions panel for the workflow to see which node failed.
