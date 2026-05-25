# Setup Guide — Lead Qualification Agent with RAG and Telegram

This guide walks you from zero to a working lead-qualification chatbot:

1. Upload a CSV / Excel / TXT file via the web tool.
2. The file's content is embedded by OpenAI and stored in Supabase as a vector knowledge base.
3. Users chat with a Telegram bot that answers questions using that knowledge base and scores them as leads.

You will set up five external services (Supabase, OpenAI, Google Gemini, Telegram, n8n) and connect them via one n8n workflow plus one local web tool.

**Estimated time:** 30–45 minutes if you start from scratch.

---

## Prerequisites

- A computer with **Python 3** installed (for serving the web tool — `python3 --version` to check).
- A web browser.
- An email account you can use to sign up for Supabase, OpenAI, Google AI Studio, and n8n.
- A phone with **Telegram** installed (to talk to BotFather).
- A credit / debit card for OpenAI billing (the embedding API isn't available on the free tier). Google Gemini has a free tier that's sufficient for development.

---

## Part 1 — Supabase

Supabase hosts the Postgres database that stores the vectorised knowledge base.

### 1.1 Create a Supabase project

1. Go to https://supabase.com/dashboard and sign up / sign in.
2. Click **New project**.
3. Pick an **organization**, give the project a **Name** (e.g. `LeadGeneration`), set a strong **Database password** (save it — you may need it later), and pick a **Region** geographically close to your users.
4. Click **Create new project**. Wait ~2 minutes for provisioning.

### 1.2 Create the `documents` table and matching RPC

The n8n LangChain Supabase Vector Store node expects a specific schema. Run this once.

1. In the left sidebar, click the **SQL Editor** icon (the `>_` symbol, third from the top).
2. Click **+ New query**.
3. Paste the following SQL:

```sql
-- Enable pgvector
create extension if not exists vector;

-- Documents table (1536-dim embeddings = OpenAI text-embedding-3-small/large default)
create table if not exists documents (
  id bigserial primary key,
  content text,
  metadata jsonb,
  embedding vector(1536)
);

-- IVFFlat index for fast cosine similarity search
create index if not exists documents_embedding_idx
  on documents using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- RPC the LangChain retriever calls
create or replace function match_documents (
  query_embedding vector(1536),
  match_count int default 5,
  filter jsonb default '{}'
) returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where documents.metadata @> filter
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;
```

4. Click **Run** (or press ⌘+Enter / Ctrl+Enter). You should see **"Success. No rows returned."**
5. Click the **Table Editor** icon (2nd in the sidebar) and confirm a `documents` table now exists under the `public` schema.

### 1.3 Collect the two values you need from Supabase

Open **Project Settings → API Keys** (gear icon at the bottom of the sidebar). You need:

| Field in n8n | Where to copy from |
|---|---|
| **Host** | The full project URL shown at the top, e.g. `https://abcd1234.supabase.co` |
| **Service Role Secret** | The **`service_role`** key — a long JWT that starts with `eyJhbGciOiJIUzI1NiI...` |

**Important:** Use the `service_role` key, **not** the `anon` / `public` / `sb_publishable_*` keys. The Vector Store node needs write permission and the `service_role` JWT bypasses Row Level Security.

If your dashboard shows the new format (`sb_publishable_*` and `sb_secret_*`), scroll down on the same page to find the **Legacy JWT keys** section. The n8n node currently expects the legacy `service_role` JWT.

⚠️ **Treat the `service_role` key like a password.** Anyone with it has full database access.

---

## Part 2 — OpenAI (embeddings only)

OpenAI is used **only for the embedding model** (`text-embedding-3-small`, 1536-dim). The chat model is Google Gemini — see Part 3.

### 2.1 Create an account and add billing

1. Go to https://platform.openai.com/signup and sign up.
2. Visit https://platform.openai.com/settings/organization/billing and add at least **$5** in credits. The free tier will not work for API calls.

### 2.2 Create an API key

1. Go to https://platform.openai.com/api-keys.
2. Click **Create new secret key**, give it a label (e.g. `n8n-leadgen-embeddings`), and copy the key. It starts with `sk-...`.
3. Save it somewhere safe — you cannot view it again after this dialog closes.

### 2.3 Quick budget tip

Embeddings (`text-embedding-3-small`, the default) are very cheap. Uploading the included 1000-row mock CSV costs under $0.05. Embedding usage is one-time per upload; ongoing chat traffic doesn't hit OpenAI.

---

## Part 3 — Google Gemini (chat model)

The AI Agent uses **Google Gemini** via the LangChain `lmChatGoogleGemini` node.

### 3.1 Create a Google AI Studio API key

1. Go to https://aistudio.google.com/app/apikey and sign in with a Google account.
2. Click **Create API key** and pick / create a Google Cloud project.
3. Copy the key (starts with `AIza...`). Save it.

The free tier (currently 15 RPM / 1M TPM on `gemini-1.5-flash`) is enough for development. If you hit 429s during testing, either wait a minute or upgrade to a paid Google Cloud billing account.

---

## Part 4 — Telegram

Telegram is the chat interface users will use to talk to the agent.

### 4.1 Create a bot via BotFather

1. In Telegram, search for the user **`@BotFather`** and start a chat.
2. Send `/newbot`.
3. BotFather asks for a **name** (any human-readable name, e.g. `BELL Lead Bot`).
4. BotFather asks for a **username** ending in `bot` (e.g. `bell_leadgen_bot`). It must be unique across all of Telegram.
5. BotFather replies with a token of the form `123456789:ABCDEF...`. **Save this token.**

### 4.2 Find your bot

In the BotFather reply there's a `t.me/<your_bot>` link. Click it, then **Start** the chat. Send any message to the bot — it won't reply yet, but this gets the chat ready.

---

## Part 5 — n8n

n8n is the workflow engine. You can run it locally or use the cloud (Hostinger, n8n Cloud, etc.).

### 5.1a Option A: n8n Cloud / hosted

1. Sign up at https://n8n.io or use your hosting provider's deployment (e.g. `https://n8n.<your-host>.cloud`).
2. Note the URL — you'll need it later.

### 5.1b Option B: local Docker

```bash
docker run -d --restart unless-stopped \
  --name n8n -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e N8N_SECURE_COOKIE=false \
  docker.n8n.io/n8nio/n8n
```

Open http://localhost:5678 and create the owner account.

> **Caveat for local n8n:** Telegram cannot deliver messages to `localhost`. For local development you can either use `ngrok` to expose your local n8n publicly (and configure n8n with `WEBHOOK_URL`), or use the cloud option for the Telegram side.

### 5.2 Import the workflow

1. In n8n, open **Workflows → Import from File** (or paste from URL).
2. Select [Lead Qualification Agent with RAG and Telegram interface.json](Lead Qualification Agent with RAG and Telegram interface.json) from this repo.
3. The workflow opens in the editor. Don't activate it yet — credentials still need to be wired up.

### 5.3 Create credentials in n8n

In n8n's left sidebar, open **Credentials** and create the following five. (Some installations call this section **Settings → Credentials**.)

#### Supabase API
- Click **New Credential → Supabase API**.
- **Host:** the Supabase project URL from §1.3 (e.g. `https://abcd1234.supabase.co`)
- **Service Role Secret:** the `service_role` JWT from §1.3
- Click **Save**. n8n will test the connection — green tick = success.

#### OpenAI API
- Click **New Credential → OpenAI**.
- **API Key:** the `sk-...` key from §2.2
- Click **Save**.

#### Google Gemini (PaLM) API
- Click **New Credential → Google Gemini(PaLM) API** (also listed as **Google PaLM**).
- **API Key:** the `AIza...` key from §3.1
- Click **Save**.

#### Telegram API
- Click **New Credential → Telegram**.
- **Access Token:** the token from BotFather in §4.1
- Click **Save**.

#### Gmail OAuth (optional)
The workflow's `Send a message` node sends a notification email when a lead's score passes 70. If you don't want this, **leave the Gmail credential out and disable that node** (right-click the node → **Disable**) or n8n will refuse to activate the workflow.

If you do want it: **New Credential → Gmail OAuth2 API**, and follow n8n's OAuth-consent flow with a Google Cloud project that has the Gmail API enabled.

### 5.4 Wire credentials onto every node that needs them

After import, each node's credential dropdown will show a warning. Open these nodes one by one and pick the matching credential from the dropdown. **Don't miss the ones marked ⚠️ — they're easy to forget:**

| Node name | Credential type | Notes |
|---|---|---|
| Google Gemini Chat Model | Google Gemini(PaLM) API | This is the chat LLM, not OpenAI |
| Embeddings OpenAI | OpenAI | (insert side) |
| Embeddings OpenAI1 | OpenAI | ⚠️ (retrieve side) |
| Supabase Vector Store | Supabase | Operation = Insert Documents, Table Name = `documents` |
| Supabase Vector Store1 | Supabase | ⚠️ Operation = Retrieve as Tool, Table Name = `documents` |
| Telegram Trigger | Telegram |  |
| Send a text message | Telegram | ⚠️ Often missed |
| Send a message | Gmail | ⚠️ If skipping Gmail, **disable** this node. The `To` field is hardcoded to `sales@sales.com` — replace with a real address before enabling. |

For the two **Supabase Vector Store** nodes, after picking the credential, click the **Table Name** dropdown — `documents` should appear. Pick it.

Inside the **AI Agent** node, confirm:
- **Chat Model** → connected to Google Gemini Chat Model
- **Memory** → connected to Simple Memory
- **Tool** → connected to Supabase Vector Store1 (the retrieve-as-tool one)

### 5.5 Activate the workflow

1. In the top-right corner of the editor, click the **Inactive** toggle to flip it to **Active**.
2. n8n will show errors here if any node still has missing credentials — fix them and try again.
3. When the toggle goes green, the workflow is live:
   - The **upload webhook** is now reachable at `<your-n8n-url>/webhook/upload-document`
   - The **Telegram webhook** has been registered with Telegram's servers automatically

You can verify the Telegram registration with:

```bash
curl "https://api.telegram.org/bot<YOUR_TELEGRAM_TOKEN>/getWebhookInfo"
```

The `url` field should match your n8n instance.

---

## Part 6 — The web tool

The static web tool parses your file in the browser and POSTs JSON to the n8n upload webhook.

### 6.1 Configure the default webhook URL (optional)

[web/index.html](web/index.html) has a default URL near the top. Edit the `value` and `placeholder` of `#webhookUrl` to match your n8n:

```html
<input id="webhookUrl" type="url"
  value="https://your-n8n.example.com/webhook/upload-document"
  placeholder="https://your-n8n.example.com/webhook/upload-document" />
```

You can also leave the default and edit the URL in the form at runtime — it persists in `localStorage`.

### 6.2 Run it

```bash
cd web
python3 -m http.server 8889
```

Open http://localhost:8889/ in your browser.

> **Why a server and not just opening the file?** Browsers block `fetch()` from `file://` to `https://` for CORS reasons. Serving over HTTP — even on localhost — fixes that.

---

## Part 7 — End-to-end test

### 7.1 Upload a document

1. Open http://localhost:8889/.
2. Confirm the webhook URL field matches your n8n.
3. Drop or browse to a CSV/Excel/TXT file. The included [web/mock_clients_1000.csv](web/mock_clients_1000.csv) is a good test file — 1000 mock client records.
4. Click **Upload to Supabase**.
5. Watch for "Uploaded successfully." Large files may take 30–60 seconds while OpenAI embeds each chunk.

### 7.2 Verify rows landed in Supabase

In the Supabase dashboard, **Table Editor → documents**. You should see rows with `content`, `metadata` (containing `source` filename and `uploaded_at`), and `embedding`.

### 7.3 Chat with the bot

1. Open Telegram and open the chat with your bot.
2. Send a message in **the exact format**: `Your Name, you@example.com`
   - The agent's first stage requires both Name and a valid email in the same message, comma-separated.
3. Once registered, ask any question about what you uploaded, e.g. *"Who in Singapore is a Data Scientist?"* or *"What's the most common income range?"*
4. The agent will:
   - Embed your question with OpenAI
   - Search Supabase for the top 5 matching chunks
   - Compose an answer using Google Gemini
   - Score you as a lead from 0–100 based on signals in the conversation
   - Reply in Telegram

If your score crosses 70 and Gmail is configured (with a real recipient — see §5.4), the workflow also sends a sales notification email.

---

## Troubleshooting

### "Failed to fetch" in the web tool
The webhook isn't reachable. Common causes:
- **Workflow not active** in n8n (check the toggle in the top-right of the editor).
- **Wrong URL in the form** — check the path is `/webhook/upload-document` (production) or `/webhook-test/upload-document` (test mode, requires clicking "Listen for test event" each time).
- **CORS** — the webhook node has `allowedOrigins: "*"` set in the JSON. If you changed it, set it back or add your web tool origin explicitly.

### Webhook returns 500
The workflow fired but errored. Open the n8n **Executions** panel for the workflow and click into the most recent failed run. The error is usually:
- A node missing credentials.
- The OpenAI key out of credits / hitting a rate limit (`429`) on the Embeddings node.
- The Google Gemini key out of free-tier quota (`429`) on the Chat Model.
- The Default Data Loader's expression broken — should be `{{ $('Upload Webhook').item.json.body.content }}` with `jsonMode = expressionData`.
- The `documents` table or `match_documents` function missing in the Supabase project the credential points at (see §1.2).

### Telegram bot doesn't reply
Run:

```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo" | python3 -m json.tool
```

- If `url` is empty → workflow isn't active. Activate it.
- If `url` points elsewhere → another n8n instance grabbed this bot's webhook. Reactivate the correct workflow (or call `setWebhook` manually with the right URL).
- If `pending_update_count > 0` → n8n is returning non-200 responses. Check Executions.
- If `pending_update_count == 0` and bot still doesn't respond → the workflow ran but didn't send a reply. Open Executions to see which node errored. The Code node now substitutes a fallback string when the agent emits non-JSON, so empty `reply_to_user` is no longer the usual culprit; suspect a Gemini 429, an OpenAI 429 on Embeddings1, or a missing credential on `Send a text message`.

### Bot keeps asking for Name and Email
The bot is doing what its system prompt says. Send a message in **exactly** this format on a single line:

```
Jane Doe, jane@acme.com
```

If you've already registered and it's still asking, the **Simple Memory** window (default 10 messages) may have rolled over your registration. Bump the **Context Window Length** on the Simple Memory node to 30 or more.

### "Cannot publish workflow: N nodes have configuration issues"
n8n is telling you which nodes lack credentials. Open each one and assign the right credential. If you're skipping Gmail, **disable** the `Send a message` node so n8n stops complaining about it.

### Bot replies with someone else's name / a stale message
If you imported an older copy of the workflow JSON, the **Telegram Trigger** may have **pinned data** from a previous test run (e.g. a fake "Amaresh Sahoo" message). In test mode that pinned payload overrides the real Telegram update, so the bot answers the wrong person.

Open the Telegram Trigger node → click the pinned data badge → **Unpin**. Or re-import the current workflow JSON in this repo, which ships with `pinData: {}`.

### Supabase service_role key isn't visible in dashboard
The new Supabase API keys UI hides the legacy JWTs by default. Look for a **Legacy JWT keys** or **JWT Settings** section on the same API page — that's where the legacy `service_role` key lives.

---

## Reference: the values you collected

Keep these somewhere safe (NOT in source control):

| Service | Field | Used in |
|---|---|---|
| Supabase | Project URL | n8n Supabase credential **Host** |
| Supabase | `service_role` JWT | n8n Supabase credential **Service Role Secret** |
| OpenAI | API key (`sk-...`) | n8n OpenAI credential **API Key** (embeddings only) |
| Google Gemini | API key (`AIza...`) | n8n Google Gemini(PaLM) credential **API Key** (chat model) |
| Telegram | Bot token (from BotFather) | n8n Telegram credential **Access Token** |
| n8n | Instance URL | Web tool **n8n Webhook URL** field (append `/webhook/upload-document`) |

The repo's `.env` is a convenient place to store them locally — it's already gitignored. The MCP servers in `.mcp.json` will pick them up if you use Claude Code with this project.
