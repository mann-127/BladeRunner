# BladeRunner — Features Reference

Complete reference for BladeRunner's capabilities.

---

## Overview

BladeRunner is a clean agentic loop: the LLM receives a prompt, calls tools, and iterates until it has a final answer. Every feature listed here is implemented and shipped.

**Optional extras:** Some features require installing extras. Use `uv sync --extra <name>` for `web`, `image`, `interactive`, `api`, `rag`, `full`, or `dev` (dev tools + everything).

---

## Agentic Loop

**What it does:** Runs the prompt → LLM → tool call → result → repeat cycle until the model produces a text-only response (no tool calls) or a limit is reached.

**Limits:**
- `agent.max_iterations` (default: 30) — stops with a `max iterations` message if exceeded
- `agent.max_history_messages` (default: 20) — oldest non-system messages are trimmed to keep context manageable

**Consecutive-failure guard:** If the same tool fails 3 times in a row, a recovery hint is injected into the conversation so the model tries a different approach instead of looping.

**Interrupt:** Set `agent.interrupted = True` at any point during execution to stop cleanly at the next iteration boundary.

**Configuration:**
```yaml
agent:
  max_iterations: 30
  max_history_messages: 20
```

---

## Tools

BladeRunner registers tools from its registry and passes their JSON Schema definitions to the LLM. The model calls them by name.

### Core tools (always registered)

| Tool | Description |
|------|-------------|
| `Read` | Read a file from disk |
| `Write` | Write content to a file |
| `Bash` | Execute a shell command with a configurable timeout |

### Optional tools

| Tool | Enabled when | Extra required | Description |
|------|-------------|----------------|-------------|
| `WebSearch` | `web_search.enabled: true` | `web` | Search DuckDuckGo or Brave |
| `FetchWebpage` | `web_search.enabled: true` | `web` | Fetch and parse a URL |
| `ReadImage` | always (if Pillow installed) | `image` | Read an image file and return a description |
| `rag_ingest` | `rag.enabled: true` | `rag` | Store documents in the vector store |
| `rag_search` | `rag.enabled: true` | `rag` | Semantic search across stored documents |

---

## Safety & Permissions

**What it does:** Intercepts tool calls before execution and either allows, prompts, or denies based on the active permission profile.

### Permission profiles

| Profile | Behaviour |
|---------|-----------|
| `strict` | Prompt before **all** tool calls |
| `standard` | Prompt only for critical operations |
| `permissive` | Allow everything without prompting |

`--permissions none` in the CLI sets the profile to `permissive` and disables the approval loop entirely (useful for automated/test runs).

### Critical operation detection

**Bash:** Commands matching destructive patterns (`rm -`, `dd`, `mkfs`, `fdisk`, `parted`, `chmod 777`, `:(){:|:&}`, etc.) are flagged as critical.

**File write:** Paths under `/etc`, `/sys`, `~/.ssh`, `~/.aws`, and files with extensions `.key`, `.pem`, `.p12`, `.pfx` are flagged.

**File read:** Paths like `.env`, `~/.aws/credentials`, `~/.ssh/id_*` are flagged.

### Approval prompt

```
⚠️  CRITICAL OPERATION REQUIRES APPROVAL

Operation: Execute bash command
Reason: Delete files with 'rm'
Details: rm -rf /old_data

Approve? (y)es / (n)o / (a)lways approve this pattern
>
```

- `y` — approve this one call
- `n` — deny this one call (tool returns a denied message)
- `a` — approve all calls matching this pattern for the rest of the session

**Configuration:**
```yaml
agent:
  require_approval: true
  permissions_profile: standard  # strict | standard | permissive
```

**CLI:**
```bash
bladerunner --permissions strict "Your task"
bladerunner --permissions permissive "Your task"
bladerunner --permissions none "Your task"   # disables approval loop
```

---

## Streaming

**What it does:** Streams response tokens in real-time as the model generates them, rather than waiting for the full response.

**Behaviour:** Streaming only applies to the final text response — tool call results are not streamed.

**CLI:**
```bash
bladerunner --stream "Your task"
```

**Config (to stream by default):**
```yaml
agent:
  stream: true
```

**API:** Set `enable_streaming: true` in the `/api/chat` request body. Streaming chunks are delivered over the `/ws/chat` WebSocket endpoint.

---

## Semantic Memory

**What it does:** Stores the execution path of successful runs and injects similar past solutions as context on new tasks.

**How it works:**
1. After a successful run, the task prompt and the tools used are saved to `~/.bladerunner/memory/solutions.jsonl`
2. On each new task, BladeRunner searches for similar past solutions (Jaccard similarity by default, or sentence-transformers if `memory_use_embeddings: true`)
3. Up to 3 similar solutions are injected into the system context

**Similarity threshold:** 30% word overlap required (Jaccard mode)

**Configuration:**
```yaml
agent:
  memory_enabled: true
  memory_use_embeddings: false          # true requires sentence-transformers
  memory_embedding_model: all-MiniLM-L6-v2
```

**Data location:** `~/.bladerunner/memory/solutions.jsonl`

---

## Session Persistence

**What it does:** Persists conversation history across CLI invocations so you can resume multi-turn projects.

**Storage:** Append-only JSONL files, one per session, in `~/.bladerunner/sessions/`.

**CLI:**
```bash
# Start a named session
bladerunner --session my-project "Create a Flask app"

# Continue the most recent session
bladerunner --continue "Add authentication"

# Resume a specific session by ID
bladerunner --resume <session-id> "Next task"

# Start fresh (ignore existing sessions)
bladerunner --new-session "New task"

# List all saved sessions
bladerunner --list-sessions
```

**Configuration:**
```yaml
sessions:
  enabled: true
  directory: ~/.bladerunner/sessions
```

---

## Web Search

**What it does:** Gives the agent access to live web search and webpage fetching.

**Providers:**

| Provider | API Key | Notes |
|----------|---------|-------|
| DuckDuckGo (default) | Not required | Zero friction, privacy-friendly |
| Brave Search | `BRAVE_API_KEY` | Higher quality, 2,000 free queries/month |

**Automatic fallback:** If Brave is configured but the key is missing, falls back to DuckDuckGo. If DuckDuckGo fails and a Brave key is available, falls back to Brave.

**Configuration:**
```yaml
web_search:
  enabled: true
  provider: duckduckgo   # or "brave"
  max_results: 5
  timeout: 10
```

---

## RAG (Retrieval-Augmented Generation)

**What it does:** Lets the agent build and query a persistent vector knowledge base. Useful for large codebases, internal documentation, or any corpus too large to fit in context.

**Installation:**
```bash
uv sync --extra rag
```

**Tools registered when enabled:**
- `rag_ingest` — embed and store documents
- `rag_search` — semantic search across stored documents

**Configuration:**
```yaml
rag:
  enabled: true
  persist_directory: ~/.bladerunner/rag
  embedding_model: all-MiniLM-L6-v2
```

**Usage:**
```bash
# Enable in config, then prompt the agent naturally:
bladerunner "Read all markdown files in docs/ and ingest them into the knowledge base"
bladerunner "Search the knowledge base for 'authentication patterns' and summarize findings"
```

**Data location:** `~/.bladerunner/rag/` (ChromaDB persistent store)

---

## Interactive Mode

**What it does:** Launches a persistent REPL so you can hold a continuous conversation without re-invoking the CLI each turn.

**Installation:**
```bash
uv sync --extra interactive
```

**Usage:** Run `bladerunner` without a prompt argument — the REPL opens automatically when `prompt_toolkit` and `rich` are installed.

**REPL commands:**
- `/help` — list available commands
- `/exit` (or Ctrl+D) — quit

**Configuration:** Input history is stored in `~/.bladerunner/history`.

---

## FastAPI Server

**What it does:** Exposes BladeRunner over HTTP and WebSocket for frontend integration or multi-user deployment.

**Installation:**
```bash
uv sync --extra api
```

**Start:**
```bash
uv run bladerunner-api
# or
docker compose up -d --build
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/auth/login` | JWT login (access + refresh tokens) |
| `POST` | `/api/auth/refresh` | Refresh access token |
| `GET` | `/api/auth/me` | Resolve current JWT identity |
| `POST` | `/api/sessions` | Create session |
| `GET` | `/api/sessions` | List sessions for a user |
| `GET` | `/api/sessions/{id}/messages` | Retrieve session messages |
| `POST` | `/api/uploads/image` | Upload image with quota/type/size checks |
| `POST` | `/api/chat` | Chat completion |
| `WS` | `/ws/chat` | Bidirectional streaming chat |

**Swagger UI:** `http://localhost:8000/docs`

### Chat request

```json
{
  "user_id": "user123",
  "message": "Refactor parser.py and add tests",
  "session_id": "session_abc",
  "model": "gemma",
  "enable_web_search": false,
  "enable_rag": false,
  "image_paths": [],
  "enable_streaming": false,
  "permission_profile": "none"
}
```

### WebSocket protocol

**Client → Server:**
```json
{"type": "interrupt"}   // Stop execution gracefully
{"type": "ping"}        // Heartbeat
```

**Server → Client:**
```json
{"type": "status",  "status": "executing"}
{"type": "chunk",   "delta": "token text"}
{"type": "final",   "answer": "...", "interrupted": false}
{"type": "pong"}
{"type": "error",   "message": "error details"}
```

---

## JWT Authentication

**What it does:** Protects all API endpoints with JWT bearer tokens. Optional static API key auth is also supported.

**Setup:**
```bash
# Generate secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
export BLADERUNNER_JWT_SECRET=your_secret

# Create user credentials
uv run bladerunner-create-user
```

**Config:**
```yaml
api:
  auth:
    enabled: true
    jwt:
      enabled: true
      secret_key: ""          # set via BLADERUNNER_JWT_SECRET
      access_token_expire_minutes: 60
      refresh_token_expire_days: 7
    users:
      - username: admin
        password_hash: $2b$12$...
        user_id: admin-001
        permissions: ["read", "write", "admin"]
```

**Login flow:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
# → {"access_token": "eyJ...", "refresh_token": "eyJ...", "expires_in": 3600}

curl http://localhost:8000/api/chat \
  -H "X-API-Key: eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"user_id": "admin", "message": "Hello"}'
```

---

## Image Workflows

**What it does:** Attaches image paths to a prompt so the agent can call `ReadImage` to provide visual context.

**Formats supported:** JPEG, PNG, GIF, WebP

**CLI:**
```bash
bladerunner --image error.png "Debug this error screenshot"
bladerunner --image img1.png --image img2.png "Compare these diagrams"
```

**API:** Use the `image_paths` field in the chat request, or upload via `POST /api/uploads/image` first.

---

## Easter-Egg Profiles

Hidden CLI flags named after Officer K's designations from Blade Runner 2049. Each sets the permission profile:

| Flag | Profile | Effect |
|------|---------|--------|
| `--officer-k` | strict | Maximum safety — approve all critical operations |
| `--constant-k` | standard | Balanced — default behaviour |
| `--agent-k` | permissive | Minimal oversight |

```bash
bladerunner --officer-k "Deploy changes"
bladerunner --agent-k "Quick prototype"
```

These flags are hidden from `--help`.

---

## See Also

- [README.md](../README.md)
- [EXAMPLES.md](EXAMPLES.md)
- [config.example.yml](../config.example.yml)
