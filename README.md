# BladeRunner v2.0.49

[![Codename](https://img.shields.io/badge/codename-KD6--3.7%20%22K%22-FF6B35.svg)](#)

**Execute orders like a Replicant. Retire the manual.**

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-green.svg)](...)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://docs.astral.sh/ruff/)
[![CI](https://github.com/mann-127/BladeRunner/actions/workflows/ci.yml/badge.svg)](https://github.com/mann-127/BladeRunner/actions)
[![Permissions: Standard](https://img.shields.io/badge/permissions-standard-orange.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Table Of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Agentic AI Features](#-agentic-ai-features)
- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [Development And Testing](#-development--testing)
- [Use Cases](#-use-cases)
- [Configuration](#-configuration)
- [Why This Matters](#-why-this-matters)

---

## 🎯 Overview

BladeRunner transforms natural language prompts into executed code and system operations through an intelligent agent architecture. Whether you're prototyping, debugging, or automating development workflows, BladeRunner provides the tools and safety guardrails you need.

### Why BladeRunner?

- **🏗️ Production-Ready**: Modular architecture designed for real-world use
- **🔒 Secure**: Three-profile permission system with command filtering
- **💾 Persistent**: Session management for multi-turn conversations
- **🌐 Connected**: Web search for real-time information
- **👁️ Image-Aware Workflows**: Path-based image context support
- **🎨 Flexible**: Modular tool system and skills framework
- **⚡ Fast**: Support for multiple model providers and aliases

---

## 📐 System Architecture

![Diagram](docs/ARCHITECTURE.png)

**Architecture Overview:**
The diagram above represents the logical execution pipeline of `bladerunner/agent.py`. The broad, gray background lines represent the macro-stages of the request, while the thin colored lines represent the granular data hand-offs between the components.

Editable source diagrams are versioned in `docs/ARCHITECTURE (light).drawio` and `docs/ARCHITECTURE (dark).drawio`.

**The Execution Lifecycle (`execute()`):**
1. **Ingestion:** User prompts enter through `cli.py` or `api.py` (HTTP/WebSocket API).
2. **Context Compilation:** `memory.py` injects similar successful past solutions, and `sessions.py` loads the ongoing conversation history.
3. **Core Generation:** `agent.py` builds the message list and calls the configured LLM backend (OpenRouter or Groq).
4. **Parsing & Guardrails:** Tool calls are parsed and intercepted by `safety.py` / `permissions.py` to check for destructive operations and request user authorization when required.
5. **Execution:** The validated command is dispatched to the tool registry (`tools/bash.py`, `tools/filesystem.py`, `tools/web.py`, `tools/image.py`, `tools/rag.py`).
6. **Loop & Memory:** Successful runs are committed to `memory.py` for future recall. If the same tool fails 3 times in a row, a recovery hint is injected into the context so the model tries a different approach.

---

**Project Structure:**

```
bladerunner/
├── __init__.py        # Package exports and version
├── __main__.py        # Module entrypoint
├── agent.py           # Core agentic loop
├── api.py             # FastAPI server (REST + WebSocket)
├── api_store.py       # SQLite persistence for API sessions/users
├── cli.py             # Command-line interface
├── config.py          # Pydantic configuration management
├── interactive.py     # Interactive REPL mode (requires --extra interactive)
├── logging_config.py  # Logging setup
├── memory.py          # Semantic memory and RAG
├── permissions.py     # Permission checker
├── py.typed           # PEP 561 typing marker
├── safety.py          # Critical operation detection and approval
├── sessions.py        # Session persistence (JSONL)
├── text_utils.py      # Shared text normalization utilities
├── tools/
│   ├── base.py        # Tool base class and ToolRegistry
│   ├── bash.py        # Shell command execution
│   ├── filesystem.py  # Read/Write file operations
│   ├── image.py       # Image reading (requires --extra image)
│   ├── rag.py         # RAG ingest/search (requires --extra rag)
│   └── web.py         # Web search and fetch (requires --extra web)
```

---

## 🧠 Agentic AI Features

BladeRunner implements a clean, production-grade agentic loop with safety and learning built in:

**Core**
- Agentic loop (LLM → tool calls → loop → final answer)
- Streaming responses
- Consecutive-failure guard (recovery hint injected after 3 consecutive failures for the same tool)
- Configurable iteration and history limits

**Safety & Learning**
- Human-in-the-Loop approvals (critical operation detection)
- Three-profile permission system (strict / standard / permissive)
- Semantic memory (recall similar past solutions)

All features are configurable. **For complete details, configuration, and examples:** See [FEATURES.md](docs/FEATURES.md)

---

## 💡 Key Features

### 🛠️ Core Tools
- **Read/Write**: Intelligent file operations with encoding support
- **Bash**: Safe command execution with timeouts
- **WebSearch**: Real-time information via DuckDuckGo (free) or Brave Search API
- **FetchWebpage**: Extract and parse web content
- **ReadImage**: Image-path tool for visual-context workflows
- **RAG Tools**: Document ingestion (`rag_ingest`) and semantic search (`rag_search`)

### 🔐 Security & Permissions
- **Three-profile system**: Strict, Standard, Permissive profiles
- **Command filtering**: Block dangerous operations (`rm -rf`, `sudo`, etc.)
- **User confirmation**: Interactive prompts for sensitive actions
- **Glob patterns**: Fine-grained file access control

### 💾 Session Management
- **Persistent conversations**: JSONL-based storage
- **Resume anytime**: Continue from where you left off
- **Session history**: List and manage multiple sessions
- **Context preservation**: Full conversation state maintained

### 🌐 Web Integration
- **Live search**: Access current information
- **Content extraction**: Parse and summarize web pages
- **Modular**: Ready for additional sources

### 👁️ Image Workflows
- **Multi-format uploads**: JPEG, PNG, GIF, WebP support
- **Path-based context**: Include uploaded paths and let the agent invoke `ReadImage`
- **Backend-dependent quality**: Visual reasoning depends on the selected model/backend

### 🔍 RAG (Retrieval-Augmented Generation)
- **Vector storage**: Persistent semantic search with ChromaDB
- **Document ingestion**: Store and embed text for later retrieval
- **Semantic search**: Find relevant context using similarity matching
- **Knowledge base**: Build and query custom document collections
- **Optional dependency**: Install with `uv sync --extra rag`

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/mann-127/BladeRunner.git
cd BladeRunner

# Install base package (core agent + CLI only)
uv sync

# Install everything including dev tools
uv sync --extra dev
```

**Optional Extras:**

| Extra | Command | Installs |
|-------|---------|----------|
| `web` | `uv sync --extra web` | Web search & fetch tools (requests, beautifulsoup4) |
| `image` | `uv sync --extra image` | Image reading tool (Pillow) |
| `interactive` | `uv sync --extra interactive` | Interactive REPL (prompt-toolkit, rich) |
| `api` | `uv sync --extra api` | FastAPI server (fastapi, uvicorn, pyjwt, bcrypt) |
| `rag` | `uv sync --extra rag` | RAG tools (chromadb, sentence-transformers) |
| `full` | `uv sync --extra full` | All optional features |
| `dev` | `uv sync --extra dev` | Dev tools (ruff, pytest) + all optional features |

**Note:** `uv sync` alone installs only the core agent. To use the API server run `uv sync --extra api`; for web search tools run `uv sync --extra web`.

### API Keys

BladeRunner supports two OpenAI-compatible backends: **OpenRouter** (default) and **Groq** (faster, free). Select the backend in your config file with `backend: openrouter` or `backend: groq`.

**OpenRouter Setup (default):**

```bash
export OPENROUTER_API_KEY="your-key-here"
# Web search uses free DuckDuckGo by default (no API key needed)
```

**Groq Setup (alternative, faster & free):**

```bash
export GROQ_API_KEY="your-groq-key"
# Web search uses free DuckDuckGo by default (no API key needed)
```

Then set `backend: groq` in your config file (`~/.bladerunner/config.yml`).

**Using .env file:**

```bash
cat > .env << EOF
OPENROUTER_API_KEY=your-key-here
# Or use Groq instead:
GROQ_API_KEY=your-groq-key

# Optional: For enhanced search quality (DuckDuckGo is used by default)
BRAVE_API_KEY=your-brave-key
EOF
```

BladeRunner auto-loads `.env` files on startup.

You can also copy the template:

```bash
cp .env.example .env
```

**Getting API Keys:**
- **OpenRouter**: Sign up at [openrouter.ai](https://openrouter.ai) for access to GPT, Llama, and many hosted models
- **Groq** (recommended for free usage): Sign up at [console.groq.com](https://console.groq.com) for free access. Check their current free tier details, extremely fast
- **Web Search** (built-in): Uses DuckDuckGo by default - no API key required!
  - Optional: Get Brave API key at [brave.com/search/api](https://brave.com/search/api) for higher quality results (2,000 queries/month free)
  - See [Web Search Providers](#web-search-providers) for configuration options

### Backend Comparison

| Backend | Speed | Cost | Free Tier | Models | Vision |
|---------|-------|------|-----------|--------|--------|
| **Groq** | ⚡⚡⚡ Fastest | Free | See console.groq.com | Llama, Mixtral | ❌ |
| **OpenRouter** | ⚡⚡ Standard | Pay-per-use | $0/mo | Broad hosted catalog | model-dependent |

**Recommendation:**
- **For learning/demos**: Use Groq (free, blazing fast)
- **For production**: Use OpenRouter with a model that fits your quality/latency needs

### Setup

Create a config file (optional but recommended):

```bash
cp config.example.yml ~/.bladerunner/config.yml
```

### Running BladeRunner

After installation, you can run BladeRunner in several ways:

**Option 1: Using `uv run` (recommended, no activation needed)**

```bash
uv run bladerunner -p "Your prompt here"
```

**Option 2: With activated virtual environment**

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
bladerunner -p "Your prompt here"
```

**Option 3: Direct Python module invocation**

```bash
uv run python -m bladerunner -p "Your prompt here"
```

**Option 4: API server (FastAPI)**

```bash
# Install API dependencies first
uv sync --extra api

# Start BladeRunner API server
uv run bladerunner-api
```

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/auth/login` | JWT authentication (login) |
| `POST` | `/api/auth/refresh` | Refresh JWT access token |
| `GET` | `/api/auth/me` | Get current user info from JWT |
| `POST` | `/api/sessions` | Create new session |
| `GET` | `/api/sessions?user_id={id}` | List user sessions |
| `GET` | `/api/sessions/{id}/messages?user_id={id}` | Get session messages |
| `POST` | `/api/uploads/image?user_id={id}` | Upload image for visual tasks |
| `POST` | `/api/chat` | Chat completion |
| `WS` | `/ws/chat` | Bidirectional streaming chat |
| `GET` | `/docs` | Swagger UI (interactive API docs) |
| `GET` | `/openapi.json` | OpenAPI schema |

**Interactive API docs:**
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

**Chat Request Example:**
```json
{
  "user_id": "user123",
  "message": "Analyze this codebase",
  "session_id": "session_abc",
  "model": "gemma",
  "enable_web_search": false,
  "enable_rag": false,
  "image_paths": [],
  "enable_streaming": false,
  "permission_profile": "none"
}
```

**WebSocket Protocol (Bidirectional):**

The WebSocket endpoint (`/ws/chat`) supports bidirectional communication:

**Client → Server (control messages):**
```json
{"type": "interrupt"}  // Stop agent execution gracefully
{"type": "ping"}       // Heartbeat check
```

**Server → Client (streaming messages):**
```json
{"type": "status", "status": "executing"}           // Execution started
{"type": "chunk", "delta": "token text"}            // Streaming token
{"type": "final", "answer": "...", "interrupted": false}  // Complete response
{"type": "pong"}                                    // Heartbeat response
{"type": "error", "message": "error details"}      // Error occurred
```

**API Authentication (Production Mode):**

BladeRunner supports two authentication methods:

**1. Static API Keys (simple, for development):**

Set in `config.yml`:
```yaml
api:
  auth:
    enabled: true
    keys: ["replace-with-strong-key"]
```

Or via environment variable:
```bash
export BLADERUNNER_API_KEYS=key1,key2
```

Then send header: `X-API-Key: your-key-here`

**2. JWT Authentication (recommended for production):**

Configure in `config.yml`:
```yaml
api:
  auth:
    enabled: true
    jwt:
      enabled: true
      secret_key: ""  # Set via BLADERUNNER_JWT_SECRET env var (32+ chars)
      access_token_expire_minutes: 60
      refresh_token_expire_days: 7
    users:
      - username: admin
        password_hash: $2b$12$...  # Generate with bladerunner-create-user
        user_id: admin-001
        permissions: ["read", "write", "admin"]
```

Generate JWT secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
export BLADERUNNER_JWT_SECRET=your_secure_random_secret
```

Create user credentials:
```bash
uv run bladerunner-create-user
# Follow prompts, then copy output to config.yml
```

Login flow:
```bash
# 1. Login to get tokens
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'

# Response:
# {"access_token": "eyJ...", "refresh_token": "eyJ...", "expires_in": 3600}

# 2. Use access token for API calls
curl http://localhost:8000/api/chat \
  -H "X-API-Key: eyJ..."  \
  -H "Content-Type: application/json" \
  -d '{"user_id": "admin", "message": "Hello"}'

# 3. Refresh expired token
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

**Upload Restrictions:**

Configure upload limits in `config.yml`:
```yaml
api:
  uploads:
    max_size_mb: 10               # Max file size per upload
    per_user_quota_mb: 100        # Total storage per user
    retention_days: 30            # Auto-delete after N days
    allowed_types:                # Allowed MIME types
      - image/jpeg
      - image/png
      - image/gif
      - image/webp
```

Check quota usage:
```bash
curl http://localhost:8000/api/uploads/quota/user123 \
  -H "X-API-Key: your-key-here"
```

**Container Deployment (single service):**

```bash
# Build and run API with Docker Compose
docker compose up -d --build

# View logs
docker compose logs -f bladerunner-api

# Stop service
docker compose down
```

Notes:
- API is exposed on `http://localhost:8000`
- Persistent runtime data is stored in `./data` (mounted to `/root/.bladerunner`)
- Environment variables are loaded from `.env`

**Option 5: System-wide install (optional)**

```bash
# Using pipx (recommended for global CLI tools)
pipx install .

# Or using pip
pip install .

# Then use anywhere:
bladerunner -p "Your prompt here"
```

## 🧪 Development & Testing

### Running Tests

```bash
# Install dev dependencies (ruff, pytest, and all optional extras)
uv sync --extra dev

# Run all tests
make test

# Or use pytest directly
uv run python -m pytest tests/

# Run with coverage report
uv run python -m pytest --cov=bladerunner --cov-report=term-missing

# Run with verbose output
uv run python -m pytest tests/ -v

```

### Test Suite Coverage

Current suite status:
- **~160 tests** across `tests/`
- Coverage includes CLI, API server/WebSocket auth flows, agent loop, tools, sessions, permissions, memory, safety, and integration behavior

To verify current status locally:

```bash
uv run python -m pytest tests/ -q
```

### Development Setup

Use the included `Makefile` for common tasks:

```bash
make install    # Install dependencies (uv sync)
make test       # Run tests (pytest)
make format     # Format code (ruff format)
make lint       # Lint and auto-fix (ruff check --fix)
make up         # Build and start API container
make logs       # Follow API container logs
make down       # Stop and remove containers
```

### Examples

See [EXAMPLES.md](docs/EXAMPLES.md) for copy-paste prompt examples covering:
- Quick prompts (API workflows, refactoring)
- Multi-turn sessions
- Web search integration
- Image-path workflows

### CI/CD

BladeRunner uses GitHub Actions for continuous integration:
- **Automated testing**: Runs on every push and pull request
- **Python 3.13**: Tests against stable Python version
- **Code quality**: Ruff (lint + format)
- **Coverage tracking**: pytest with cov reporting
- **Fast feedback**: Tests complete in ~30 seconds

---

## 🧑‍💻 Use Cases

### Development Automation
```bash
uv run bladerunner -p "Create a FastAPI project with auth, tests, and docs"
```

### Code Review
```bash
uv run bladerunner -p "Review auth.py for security issues — look for SQL injection, XSS, and hardcoded secrets"
```

### Research & Implement
```bash
uv run bladerunner -p "Research OAuth2 PKCE flow and implement it"
```

### Multi-Session Projects
```bash
# Day 1: Foundation
uv run bladerunner --session api-build -p "Create Flask app structure"

# Day 2: Features
uv run bladerunner --continue -p "Add user authentication"

# Day 3: Testing
uv run bladerunner --continue -p "Write comprehensive tests"
```

### Visual Debugging
```bash
uv run bladerunner --image error.png -p "Explain this error and suggest fixes"
```

### RAG-Enhanced Context
```bash
# First, enable RAG in config.yml:
# rag:
#   enabled: true

# Ingest documentation into knowledge base
uv run bladerunner -p "Read all markdown files in docs/ and use rag_ingest to store them"

# Query with context from knowledge base
uv run bladerunner -p "Use rag_search to find information about deployment, then create a deployment script"
```

---

## 🔧 Configuration

### Model Selection

BladeRunner supports two backends with different model offerings:

**OpenRouter Backend (default, free aliases):**

| Model | Provider | Cost | Best For | Speed |
|-------|----------|------|----------|-------|
| **gemma (gemma-3-27b-it)** | Google | **FREE** | Default baseline | ⚡⚡ |
| **gpt-oss-20b** | OpenAI | **FREE** | Fast reasoning | ⚡⚡ |
| **qwen3-coder** | Qwen | **FREE** | Code tasks | ⚡⚡ |
| **llama-70b** | Meta | **FREE** | General-purpose quality | ⚡ |

**Groq Backend (fast & free):**

| Model | Provider | Cost | Best For | Speed |
|-------|----------|------|----------|-------|
| **llama-3.1-70b** | Meta | **FREE** | General purpose | ⚡⚡⚡ FASTEST |
| **mixtral-8x7b** | Mistral | **FREE** | Complex tasks | ⚡⚡⚡ FASTEST |

**Using models:**

```bash
# OpenRouter models (default backend)
uv run bladerunner --model gemma -p "Your task"       # Default free Gemma
uv run bladerunner --model gpt-oss-20b -p "Your task" # Free OpenAI OSS model
uv run bladerunner --model qwen3-coder -p "Your task" # Free coding-focused model

# Groq models (set backend=groq in config)
uv run bladerunner --model groq-llama -p "Your task"   # Llama 70B (free, fastest!)
uv run bladerunner --model groq-mixtral -p "Your task" # Mixtral (free, fastest!)

# Or use full model names
uv run bladerunner --model google/gemma-4-31b-it:free -p "Your task"
```

**Default model note:** The default alias is `gemma` — a free OpenRouter baseline.

**For learning/demos:** Use `gemma`, `gpt-oss-20b`, or Groq backend.  
**For stronger quality:** Use higher-parameter aliases like `llama-70b`.

### Configuration File

Create `~/.bladerunner/config.yml`:

```yaml
# Backend selection: openrouter (default) or groq
backend: openrouter

# Model alias or full model name
model: gemma

# Agent behaviour
agent:
  require_approval: true         # prompt before critical operations
  permissions_profile: standard  # strict | standard | permissive
  memory_enabled: true
  stream: false

# Sessions
sessions:
  enabled: true

# Web search (DuckDuckGo by default — no API key needed)
web_search:
  enabled: false
  provider: duckduckgo  # or "brave" (requires BRAVE_API_KEY)
  max_results: 5

# Logging (API + uvicorn)
logging:
  level: INFO
  uvicorn_access_log: true
```

See [config.example.yml](config.example.yml) for the full reference with all options.

### Web Search Providers

BladeRunner supports multiple web search providers with **DuckDuckGo as the default** (no API key required!).

**Built-in Providers:**

| Provider | API Key Required | Free Tier | Quality | Setup |
|----------|-----------------|-----------|---------|-------|
| **DuckDuckGo** (default) | ❌ No | Unlimited | Good | ⭐ None needed |
| **Brave Search** | ✅ Yes | 2,000/month | Better | ⭐ Easy |

**Configuration:**

```yaml
web_search:
  enabled: true
  provider: duckduckgo  # or "brave"
  max_results: 5
```

**Automatic Fallback:**
- If Brave is set but API key is missing → Falls back to DuckDuckGo
- If DuckDuckGo fails and Brave key is available → Falls back to Brave

**Why DuckDuckGo as default?**
- Zero friction: Works out of the box
- Privacy-focused: No tracking
- No rate limits for reasonable usage
- Perfect for learning, demos, and personal projects

**When to use Brave:**
- Need higher quality search results
- Building portfolio/production projects
- Want structured API responses

**To add custom providers:** Extend the `WebSearchTool` class in `bladerunner/tools/web.py` to support additional providers like Tavily, Serper, or Google Custom Search.

---

## 🌟 Why This Matters

BladeRunner showcases:

1. **Agent Architecture**: Clean tool orchestration and state management
2. **Production Patterns**: Modular design, Pydantic configuration, error handling
3. **Security**: Multi-profile permission system for autonomous agents
4. **Image-Aware AI**: Integration of text workflows with image-path context
5. **Real-world Features**: Session persistence, web search, semantic memory, RAG
6. **Code Quality**: Type hints, documentation, modular design

Perfect for demonstrating **Agentic AI** and **AI Engineer** capabilities.

**Built with ❤️ for AI, automation, robotics, and the film, to demonstrate production-ready AI agent architecture, with hidden easter-eggs from the film 👀.**
