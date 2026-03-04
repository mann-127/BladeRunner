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

Use specialized capabilities with custom-defined agent behaviors.

### Using Skills

```bash
# List available skills
uv run bladerunner --list-skills

# Use a specific skill
uv run bladerunner --skill code-reviewer -p "Review main.py"

# Skills can restrict available tools
uv run bladerunner --skill read-only -p "Analyze this codebase"
```

### Creating Custom Skills

Skills are defined as Markdown files with YAML frontmatter. Create them in `~/.bladerunner/skills/`:

**Step 1:** Create skill directory and file:
```bash
mkdir -p ~/.bladerunner/skills/my-skill
```

**Step 2:** Create `~/.bladerunner/skills/my-skill/SKILL.md`:

```markdown
---
name: code-optimizer
description: Optimize Python code for performance and readability
tools: [Read, Write, Bash]
model: sonnet
temperature: 0.3
---

You are a specialized Python performance optimization expert.

When given code to optimize:

1. **Read and analyze** - Understand the current implementation
2. **Identify bottlenecks** - Find performance issues (loops, I/O, algorithms)
3. **Refactor** - Apply optimization patterns:
   - List comprehensions over loops
   - Generator expressions for large data
   - Proper data structures (sets vs lists)
   - Caching with functools.lru_cache
4. **Preserve functionality** - Never break existing behavior
5. **Add comments** - Explain optimizations made
6. **Benchmark** - Show before/after improvements

Focus on readability AND performance.
```

**Step 3:** Use your skill:
```bash
uv run bladerunner --skill code-optimizer -p "Optimize the data processing in analytics.py"
```

### Skill Schema

**Required frontmatter fields:**
- `name`: Unique skill identifier (kebab-case)
- `description`: Brief description of skill purpose

**Optional frontmatter fields:**
- `tools`: List of allowed tools (restricts agent to these tools only)
  - Available: `Read`, `Write`, `Bash`, `WebSearch`, `FetchWebpage`, `ReadImage`, `rag_ingest`, `rag_search`
- `model`: Default model for this skill (e.g., `haiku`, `sonnet`, `opus`)
- `temperature`: Temperature setting (0.0-1.0, lower = more focused)

**Body:** The skill's system prompt (instructions for the agent)

### Example Skills

**Read-Only Auditor:**
```markdown
---
name: security-auditor
description: Audit code for security vulnerabilities
tools: [Read]
temperature: 0.2
---

You are a security auditor. Analyze code for:
- SQL injection risks
- XSS vulnerabilities  
- Insecure dependencies
- Hardcoded secrets

Provide a detailed security report with severity ratings.
```

**Documentation Generator:**
```markdown
---
name: doc-generator
description: Generate comprehensive documentation
tools: [Read, Write]
model: opus
temperature: 0.6
---

You are a technical writer. Create clear, comprehensive documentation:
- API references with examples
- Usage guides for end users
- Architecture explanations
- Installation instructions

Use Markdown formatting and ensure all code examples are tested.
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

## Backend Configuration

BladeRunner supports multiple LLM backends with automatic switching.

### Available Backends

**OpenRouter (default):**
- Supports all Claude models (Haiku, Sonnet, Opus)
- Vision capabilities (image analysis)
- Free tier models (Llama, Gemini, Mistral)
- API Key: `OPENROUTER_API_KEY`

**Groq:**
- Ultra-fast inference (14,400 requests/day free)
- Llama 70B and Mixtral 8x7B
- No vision support
- API Key: `GROQ_API_KEY`

### Switching Backends

The backend is automatically selected based on your chosen model:

```bash
# OpenRouter models (default)
uv run bladerunner --model haiku -p "Your task"
uv run bladerunner --model sonnet -p "Your task"
uv run bladerunner --model llama -p "Your task"

# Groq models (auto-switches to Groq backend)
uv run bladerunner --model groq-llama -p "Your task"
uv run bladerunner --model groq-mixtral -p "Your task"
```

### Custom Backend Configuration

Add custom backends in `config.yml`:

```yaml
backends:
  openrouter:
    base_url: https://openrouter.ai/api/v1
    api_key_env: OPENROUTER_API_KEY
  
  groq:
    base_url: https://api.groq.com/openai/v1
    api_key_env: GROQ_API_KEY
  
  # Add your own backend
  custom:
    base_url: https://api.example.com/v1
    api_key_env: CUSTOM_API_KEY
```

### Model Aliases

Define custom model aliases with specific settings:

```yaml
models:
  my-fast-model:
    full_name: meta-llama/llama-3.1-8b-instruct:free
    temperature: 0.5
    max_tokens: 2048
    backend: openrouter  # Optional: specify backend
```

```bash
# Use your custom alias
uv run bladerunner --model my-fast-model -p "Your task"
```

### Environment Variables

Set up your API keys:

```bash
# OpenRouter (for Claude, Llama, Gemini, Mistral)
export OPENROUTER_API_KEY="sk-or-v1-..."

# Groq (for ultra-fast Llama and Mixtral)
export GROQ_API_KEY="gsk_..."

# Web search (optional)
export BRAVE_API_KEY="..."

# Or use a .env file
echo 'OPENROUTER_API_KEY=sk-or-v1-...' > .env
echo 'GROQ_API_KEY=gsk_...' >> .env
```

---

## Interactive Mode

Detailed guide to BladeRunner's REPL interface.

### Starting Interactive Mode

```bash
# Basic interactive mode
uv run bladerunner -i

# Interactive with specific model
uv run bladerunner -i --model sonnet

# Interactive with session
uv run bladerunner -i --session my-project
```

### Available Commands

```
/help              Show all available commands
/clear             Clear conversation history and screen
/history           Display full conversation history
/model [name]      Show current model or switch to new model
/exit              Exit interactive mode (or Ctrl+D)
/quit              Same as /exit
```

### Features

**Command History:**
- Press ↑/↓ to navigate through previous prompts
- History persisted to `~/.bladerunner/history`
- Auto-suggestions based on past commands

**Streaming Responses:**
- Enabled by default in interactive mode
- See AI responses appear token-by-token
- Real-time feedback

**Multi-line Input:**
- Single-line by default
- For longer prompts, use external editor or paste

**Session Integration:**
- Continue conversations across restarts
- Full context preserved

### Example Session

```
$ uv run bladerunner -i
BladeRunner Interactive Mode
Type /help for commands, Ctrl+D to exit

You: Create a simple Flask API

Assistant: I'll create a basic Flask API...
[creates files and shows output]

You: /model
Current model: haiku

You: /model sonnet
Switched to model: sonnet

You: Add authentication
[continues with new model]

You: /history
Conversation History:
You: Create a simple Flask API
Assistant: I'll create a basic Flask API...
You: Add authentication
...

You: /clear
Conversation cleared

You: /exit
Goodbye!
```

---

## Profile Presets (Easter Eggs)

BladeRunner includes profile presets named after Officer K's designations from Blade Runner 2049:

```bash
# Officer K - Maximum safety (strict approvals)
uv run bladerunner --profile officer-k -p "Deploy to production"

# Constant K - Balanced approach (default settings)
uv run bladerunner --profile constant-k -p "Refactor code"

# Agent K - Autonomous mode (minimal oversight)
uv run bladerunner --profile agent-k -p "Quick prototype"
```

**Profile Configurations:**

| Profile | Permissions | Planning | Reflection | Approvals |
|---------|-------------|----------|------------|----------|
| officer-k | strict | ✅ | ✅ | ✅ |
| constant-k | standard | ✅ | ❌ | ✅ |
| agent-k | permissive | ❌ | ❌ | ❌ |

**Hidden flags** (same as profiles):
```bash
uv run bladerunner --officer-k -p "Your task"
uv run bladerunner --constant-k -p "Your task"
uv run bladerunner --agent-k -p "Your task"
```

---

## See Also

- [README.md](../README.md)
- [config.example.yml](../config.example.yml) - Configuration reference
