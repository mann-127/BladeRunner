# BladeRunner Examples

Copy-paste ready examples covering all BladeRunner capabilities.

---

## Basic Usage

```bash
# Run a task
bladerunner "Create a FastAPI app with health check"

# Using -p flag
bladerunner -p "Refactor auth.py for clarity and tests"

# Stream tokens as they arrive
bladerunner --stream "Explain this codebase"
```

---

## Sessions (Persistent Conversations)

Build complex projects across multiple turns:

```bash
# Start a named session
bladerunner --session my-app "Create a Flask REST API"

# Continue the most recent session
bladerunner --continue "Add authentication"
bladerunner --continue "Add database models"
bladerunner --continue "Write unit tests"

# List all saved sessions
bladerunner --list-sessions

# Resume a specific session by ID
bladerunner --resume <session-id> "Your next task"

# Force a new session (ignore history)
bladerunner --new-session "Fresh start"
```

---

## Model Selection

```bash
# Default (free, OpenRouter)
bladerunner --model gemma "Quick task"

# Other free OpenRouter aliases
bladerunner --model llama-70b "General purpose"
bladerunner --model qwen3-coder "Code tasks"
bladerunner --model gpt-oss-20b "Template code"

# Groq backend (ultra-fast free inference)
# Set backend: groq in config.yml first
bladerunner --model groq-llama "Your task"
bladerunner --model groq-mixtral "Your task"

# Full model name
bladerunner --model meta-llama/llama-3.1-8b-instruct:free "Your task"
```

---

## Backend Configuration

BladeRunner supports OpenRouter (default) and Groq. Set the backend in `~/.bladerunner/config.yml`:

```yaml
# OpenRouter (default)
backend: openrouter
model: gemma

# Groq (faster, free tier)
backend: groq
model: groq-llama
```

Set the matching API key:
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
# or
export GROQ_API_KEY="gsk_..."
```

---

## Permission Profiles

```bash
# Strict: prompt before every critical operation
bladerunner --permissions strict "Deploy changes"

# Standard: prompt only for destructive operations (default)
bladerunner --permissions standard "Write code"

# Permissive: minimal prompts
bladerunner --permissions permissive "Automate this"

# None: disable approval loop entirely (for automated/test runs)
bladerunner --permissions none "Do whatever"
```

---

## Complex Workflows

### Multi-Turn Project Development

```bash
# Day 1: Foundation
bladerunner --session api-build "Create Flask app structure"

# Day 2: Add features
bladerunner --continue "Add user authentication"

# Day 3: Add testing
bladerunner --continue "Write comprehensive tests"
```

### Research & Implement Pattern

```bash
bladerunner "Research OAuth2 PKCE flow"
bladerunner "Implement OAuth2 PKCE in our FastAPI app"
bladerunner "Write tests for OAuth2 implementation"
```

---

## Web Search Integration

```bash
# Enable web search in config.yml first:
#   web_search:
#     enabled: true

# DuckDuckGo — works out of the box, no key required
bladerunner "What's the latest Python version? Implement a feature using it."

# Optional: use Brave for higher quality results
export BRAVE_API_KEY="your-brave-key"
bladerunner "Find the latest FastAPI patterns and implement a REST API using them"
```

---

## Image Analysis

```bash
# Single image
bladerunner --image error.png "Debug this error screenshot"

# Multiple images
bladerunner --image img1.png --image img2.png "Compare these diagrams"
```

---

## RAG (Retrieval-Augmented Generation)

```bash
# Install RAG dependencies first
uv sync --extra rag

# Enable in config.yml:
#   rag:
#     enabled: true

# Ingest documents
bladerunner "Read all markdown files in docs/ and ingest them into the knowledge base"

# Query
bladerunner "Search the knowledge base for 'authentication patterns' and summarize findings"

# Multi-step RAG workflow
bladerunner --session kb-build "Ingest all Python files from src/ into the knowledge base"
bladerunner --continue "Search for 'database connection' patterns"
bladerunner --continue "Generate a best practices document based on the results"
```

---

## API Server

```bash
uv run bladerunner-api
```

Optional auth setup:
```bash
export BLADERUNNER_API_KEYS="dev-key-1,dev-key-2"
export BLADERUNNER_JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

Create a session:
```bash
curl -X POST http://127.0.0.1:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo-user","title":"Case File"}'
```

JWT login:
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'
```

Chat:
```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo-user",
    "message": "Refactor parser.py and add tests",
    "enable_web_search": false,
    "enable_streaming": false,
    "permission_profile": "none"
  }'
```

WebSocket streaming with interrupt:
```javascript
const ws = new WebSocket("ws://127.0.0.1:8000/ws/chat");

ws.onopen = () => {
  ws.send(JSON.stringify({
    user_id: "demo-user",
    message: "Draft migration plan",
    enable_streaming: true,
    permission_profile: "none"
  }));
};

ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.type === "chunk")  process.stdout.write(msg.delta);
  if (msg.type === "status") console.log("status:", msg.status);
  if (msg.type === "final")  console.log("\nfinal:", msg.answer);
};

// Interrupt long-running tasks
setTimeout(() => ws.send(JSON.stringify({ type: "interrupt" })), 1500);
```

---

## Easter-Egg Profiles

Hidden flags named after Officer K's designations from Blade Runner 2049:

```bash
# Officer K — strict permissions (approve all critical ops)
bladerunner --officer-k "Deploy to production"

# Constant K — standard permissions (default behaviour)
bladerunner --constant-k "Refactor code"

# Agent K — permissive (minimal oversight)
bladerunner --agent-k "Quick prototype"
```

---

## See Also

- [README.md](../README.md)
- [FEATURES.md](FEATURES.md)
- [config.example.yml](../config.example.yml)
