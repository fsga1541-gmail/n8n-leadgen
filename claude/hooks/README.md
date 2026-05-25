# Project hooks

Three Claude Code harness hooks that fire on Claude's tool calls in this repo.
Configured in [`.claude/settings.json`](../settings.json).

| Hook | Event | Fires when | Action |
|---|---|---|---|
| [`validate-workflow-json.sh`](validate-workflow-json.sh) | PostToolUse: Edit / Write / MultiEdit | Claude just edited any file | If the touched file is `Lead Qualification Agent with RAG and Telegram interface.json`, run `python3 -m json.tool`. On parse failure, print a loud stderr warning so Claude self-corrects on the next turn. |
| [`pre-upload-check.sh`](pre-upload-check.sh) | PreToolUse: Bash | Claude is about to run a shell command | If the command POSTs to `/webhook/upload-document`, do a fast HEAD on the n8n root first. Logs reachability so we don't waste a request on a stopped instance. |
| [`post-upload-notify.sh`](post-upload-notify.sh) | PostToolUse: Bash | Claude just ran a shell command | If the command was a webhook upload OR `git push`, parse the response and fire a macOS desktop notification (`osascript`). Notifications are cosmetic — they degrade gracefully on Linux/Windows. |

## Why hooks instead of agent instructions?

Agent prompts live in markdown and depend on Claude reading + remembering them.
Hooks are deterministic — they fire on the matcher regardless of context length,
which is the right tool for safety checks (the JSON validator) and side effects
(notifications).

## Conventions

- **Stdin format:** Every hook receives the standard Claude Code envelope as JSON on stdin: `{ tool_name, tool_input, tool_response, ... }`. We use Python (always available) instead of `jq` (often not).
- **Exit codes:** `0` = continue, `1` = warn but continue, `2` = block. None of these hooks block — they only warn loudly.
- **No-op fast path:** Each hook returns early when the tool input doesn't match its trigger pattern. Hooks fire on every Bash/Edit, so they need to be cheap.

## Disabling locally

To turn hooks off for personal use without committing the change, override in `.claude/settings.local.json` (gitignored):

```json
{ "hooks": {} }
```

## Adding a new hook

1. Drop a script in this folder, `chmod +x` it.
2. Add an entry under the right event in `.claude/settings.json` with `"command": "$CLAUDE_PROJECT_DIR/.claude/hooks/your-script.sh"`.
3. Test with a manual stdin pipe:
   ```bash
   echo '{"tool_name":"Bash","tool_input":{"command":"curl http://localhost:5678/webhook/upload-document -d {}"}}' \
     | .claude/hooks/pre-upload-check.sh
   ```
