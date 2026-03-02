# BladeRunner Examples

Comprehensive examples covering all BladeRunner capabilities. Copy-paste ready!

---

## Basic Usage

### Simple Commands

```bash
# Generate a simple API skeleton
uv run bladerunner -p "Create a FastAPI app with health check"

# Refactor a module
uv run bladerunner -p "Refactor auth.py for clarity and tests"

# Interactive mode (REPL)
uv run bladerunner -i
```

---

## Sessions (Persistent Conversations)

Build complex projects across multiple turns:

```bash
# Start a new session
uv run bladerunner --session my-app -p "Create a Flask REST API"

# Continue the session
uv run bladerunner --continue -p "Add authentication"

# Keep building
uv run bladerunner --continue -p "Add database models"
uv run bladerunner --continue -p "Write unit tests"

# List all sessions
uv run bladerunner --list-sessions

# Resume a specific session
uv run bladerunner --resume <session-id> -p "Your next task"
```

---

## Model Selection

Switch models based on task complexity and cost:

```bash
# Claude Haiku (fast & capable, default)
uv run bladerunner --model haiku -p "Quick refactor"

# Claude Sonnet (balanced)
uv run bladerunner --model sonnet -p "Complex analysis"

# Claude Opus (most capable)
uv run bladerunner --model opus -p "Research and design architecture"

# FREE alternatives (OpenRouter)
uv run bladerunner --model llama -p "Simple task"      # Meta Llama
uv run bladerunner --model gemini -p "Quick test"      # Google Gemini
uv run bladerunner --model mistral -p "Template code"  # Mistral

# Groq models (fastest free tier, requires backend: groq)
uv run bladerunner --model groq-llama -p "Your task"    # Llama 70B, extremely fast
uv run bladerunner --model groq-mixtral -p "Your task"  # Mixtral 8x7B, extremely fast

# Full model names
uv run bladerunner --model meta-llama/llama-3.1-8b-instruct:free -p "Your task"
```

---

## Permission Profiles

Control how much approval is required:

```bash
# Strict: Approve everything (most interactive)
uv run bladerunner --permissions strict -p "Deploy changes"

# Standard: Approve critical operations only (default)
uv run bladerunner --permissions standard -p "Write code"

# Permissive: Minimal approvals (use with caution)
uv run bladerunner --permissions permissive -p "Automate this"

# None: No safety checks (dangerous!)
uv run bladerunner --permissions none -p "Do whatever"
```

---

## Agentic AI Features

See [FEATURES.md](docs/FEATURES.md) for comprehensive feature documentation and detailed examples.

### Quick Examples

```bash
# Planning & Decomposition: Agent creates a plan first
uv run bladerunner -p "Analyze this CSV and create a summary dashboard"

# Real-time Streaming: See tokens appear as generated
uv run bladerunner -p "Explain machine learning" --stream

# Error Recovery: Agent self-corrects when tools fail
uv run bladerunner -p "Find and update config.json"

# Disable Tier 1 features for speed
uv run bladerunner -p "Your task" --no-planning --no-reflection --no-retry
```

---

## Complex Workflows

### Multi-Turn Project Development

```bash
# Day 1: Foundation
uv run bladerunner --session webapp -p "Create Flask app structure"

# Day 2: Add features
uv run bladerunner --continue -p "Add user authentication"

# Day 3: Add testing
uv run bladerunner --continue -p "Write comprehensive tests"
```

### Research & Implement Pattern

```bash
# Research
uv run bladerunner -p "Research OAuth2 PKCE flow"

# Implement
uv run bladerunner -p "Implement OAuth2 PKCE in our FastAPI app"

# Test
uv run bladerunner -p "Write tests for OAuth2 implementation"
```

### Code Review Workflow

```bash
# Analyze for issues
uv run bladerunner --skill code-reviewer -p "Review auth.py for security issues"

# Refactor
uv run bladerunner -p "Refactor auth.py for clarity and add type hints"

# Test
uv run bladerunner -p "Write tests for the refactored code"
```

---

## Web Search Integration

Access real-time information:

```bash
# Set up API key
export BRAVE_API_KEY="your-brave-search-api-key"

# Web search example
uv run bladerunner -p "What's the latest Python version and implement a feature using it?"

# Combined with sessions
uv run bladerunner --session research -p "Find the latest FastAPI patterns"
uv run bladerunner --continue -p "Implement a REST API using those patterns"
```

---

## Image Analysis

Analyze screenshots and visual content:

```bash
# Single image
uv run bladerunner --image error.png -p "Debug this error screenshot"

# Multiple images
uv run bladerunner --image img1.png --image img2.png -p "Compare these diagrams"
```

---

## RAG (Retrieval-Augmented Generation)

Build and query knowledge bases with semantic search:

### Setup

```bash
# Install RAG dependencies
uv sync --extra rag

# Enable in config.yml
# rag:
#   enabled: true
```

### Basic Usage

```bash
# Ingest documents into knowledge base
uv run bladerunner -p "Read all markdown files in docs/ and use rag_ingest to store them"

# Search knowledge base
uv run bladerunner -p "Use rag_search to find information about deployment"

# Combine search with action
uv run bladerunner -p "Search the knowledge base for authentication patterns, then implement them"
```

### Advanced Examples

```bash
# Build documentation knowledge base
uv run bladerunner -p "Find all .md files, read them, and ingest into RAG with metadata"

# Query with context
uv run bladerunner -p "Search RAG for 'error handling', then write a guide based on the results"

# Multi-step RAG workflow
uv run bladerunner --session kb-build -p "Ingest all Python files from src/ into the knowledge base"
uv run bladerunner --continue -p "Search for 'database connection' patterns"
uv run bladerunner --continue -p "Generate best practices document based on the search results"
```

### Use Cases

- **Documentation search**: Query internal docs and wikis
- **Code pattern discovery**: Find similar code across large codebases
- **Onboarding**: Build knowledge bases for new team members
- **Compliance**: Store and search regulatory documents

---

## Skills

Use specialized capabilities:

```bash
# List available skills
uv run bladerunner --list-skills

# Use a specific skill
uv run bladerunner --skill code-reviewer -p "Review main.py"
```

---

## Performance Tuning

```bash
# Fastest: Groq + no planning/reflection
uv run bladerunner --model groq-llama -p "Your task" --no-planning --no-reflection

# Most reliable: Claude Sonnet + strict approvals
uv run bladerunner --model sonnet -p "Your task" --permissions strict

# Budget-friendly: Free Llama model
uv run bladerunner --model llama -p "Your task"
```

---

## See Also

- [README.md](../README.md) - Quick start and feature overview
- [FEATURES.md](../docs/FEATURES.md) - Detailed agentic AI feature documentation
- [config.example.yml](../config.example.yml) - Configuration reference
