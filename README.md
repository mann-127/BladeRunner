# BladeRunner v2.0.49

[![Codename](https://img.shields.io/badge/codename-KD6--3.7%20%22K%22-FF6B35.svg)](#)

**Execute orders like a Replicant. Retire the manual. Autonomous AI agent framework.**

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-green.svg)](...)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](...)

---

## 🎯 Overview

BladeRunner transforms natural language prompts into executed code and system operations through an intelligent agent architecture. Whether you're prototyping, debugging, or automating development workflows, BladeRunner provides the tools and safety guardrails you need.

### Why BladeRunner?

- **🏗️ Production-Ready**: Modular architecture designed for real-world use
- **🔒 Secure**: Three-tier permission system with command filtering
- **💾 Persistent**: Session management for multi-turn conversations
- **🌐 Connected**: Web search for real-time information
- **👁️ Multimodal**: Vision capabilities for image analysis
- **🎨 Flexible**: Modular tool system and skills framework
- **⚡ Fast**: Support for multiple models (Claude, Llama, Gemini, Mistral, and more)

---

## 🧠 Agentic AI Features

BladeRunner implements **8 production-grade agentic AI features** for intelligent task execution across two tiers:

**Tier 1: Strategic Thinking & Resilience**
- Planning & Decomposition
- Reflection & Self-Correction
- Error Recovery & Retry
- Streaming Responses

**Tier 2: Safety & Learning**
- Human-in-the-Loop Approvals
- Tool Effectiveness Tracking
- Semantic Memory
- Multi-Agent Orchestration

All features are configurable and optional. **For complete details, configuration, CLI usage, and examples:** See [AGENTIC-AI.md](AGENTIC-AI.md)

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/mann-127/BladeRunner.git
cd BladeRunner

# Install dependencies
uv sync
```

### API Keys

BladeRunner supports two backends: **OpenRouter** (default) or **Groq** (faster, free).

**OpenRouter Setup (default):**

```bash
export OPENROUTER_API_KEY="your-key-here"
export BRAVE_API_KEY="your-brave-key"  # Optional: web search
```

**Groq Setup (alternative, faster & free):**

```bash
export GROQ_API_KEY="your-groq-key"
export BRAVE_API_KEY="your-brave-key"  # Optional: web search
```

Then set `backend: groq` in your config file (`~/.bladerunner/config.yml`).

**Using .env file:**

```bash
cat > .env << EOF
# Choose one backend:
OPENROUTER_API_KEY=your-key-here
# OR
GROQ_API_KEY=your-groq-key

# Optional:
BRAVE_API_KEY=your-brave-key
EOF
```

BladeRunner auto-loads `.env` files on startup.

**Getting API Keys:**
- **OpenRouter**: Sign up at [openrouter.ai](https://openrouter.ai) for access to Claude, GPT, Llama, and more
- **Groq** (recommended for free usage): Sign up at [console.groq.com](https://console.groq.com) - 14,400 free requests/day, extremely fast
- **Brave Search** (optional): Get a free API key at [brave.com/search/api](https://brave.com/search/api) for web search (2,000 queries/month free)
  - See [Web Search Alternatives](#web-search-alternatives) for other options like Tavily or Serper

### Backend Comparison

| Backend | Speed | Cost | Free Tier | Models | Vision |
|---------|-------|------|-----------|--------|--------|
| **Groq** | ⚡⚡⚡ Fastest | Free | 14.4K req/day | Llama, Mixtral | ❌ |
| **OpenRouter** | ⚡⚡ Standard | Pay-per-use | $0/mo | All (Claude, GPT, etc.) | ✅ |

**Recommendation:**
- **For learning/demos**: Use Groq (free, blazing fast)
- **For production**: Use OpenRouter + Claude (better tool-calling, vision support)

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

**Option 4: System-wide install (optional)**

```bash
# Using pipx (recommended for global CLI tools)
pipx install .

# Or using pip
pip install .

# Then use anywhere:
bladerunner -p "Your prompt here"
```

**For comprehensive CLI examples and common workflows:** See [EXAMPLES.md](EXAMPLES.md)

## 🧪 Development & Testing

### Running Tests

```bash
# Run all tests
make test

# Or use pytest directly
uv run pytest tests/

# Run with coverage report
uv run pytest --cov=bladerunner --cov-report=term-missing

# Run with verbose output
uv run pytest tests/ -v
```

### Test Suite Coverage

BladeRunner includes 28+ tests covering:
- **Core imports & initialization** (framework startup)
- **CLI behavior** (version, verbose output, arguments)
- **Safety detection** (critical operations, file paths)
- **Tool tracking** (success rates, reliability ranking)
- **Semantic memory** (solution storage, similarity matching)
- **Agent orchestration** (routing, specialization)
- **Config management** (defaults, path resolution)
- **Sessions** (persistence, history)
- **Skills** (loading, parsing)

### Development Setup

Use the included `Makefile` for common tasks:

```bash
make install    # Install dependencies (uv sync)
make test       # Run tests (pytest)
make format     # Format code (black)
make lint       # Lint code (flake8)
make type       # Type-check code (mypy)
```

### Examples

See [EXAMPLES.md](EXAMPLES.md) for copy-paste prompt examples covering:
- Quick prompts (API workflows, refactoring)
- Multi-turn sessions
- Web search integration
- Vision capabilities

### CI/CD

BladeRunner uses GitHub Actions for continuous integration:
- **Automated testing**: Runs on every push and pull request
- **Python 3.13**: Tests against stable Python version
- **Code quality**: Black, Flake8, mypy linting
- **Coverage tracking**: pytest with cov reporting
- **Fast feedback**: Tests complete in ~30 seconds

---

## ✨ Key Features

### 🛠️ Core Tools
- **Read/Write**: Intelligent file operations with encoding support
- **Bash**: Safe command execution with timeouts
- **WebSearch**: Real-time information via Brave Search API
- **FetchWebpage**: Extract and parse web content
- **ReadImage**: Vision-based image analysis

### 🔐 Security & Permissions
- **Three-tier system**: Strict, Standard, Permissive profiles
- **Command filtering**: Block dangerous operations (`rm -rf`, `sudo`, etc.)
- **User confirmation**: Interactive prompts for sensitive actions
- **Glob patterns**: Fine-grained file access control

### 💾 Session Management
- **Persistent conversations**: JSONL-based storage
- **Resume anytime**: Continue from where you left off
- **Session history**: List and manage multiple sessions
- **Context preservation**: Full conversation state maintained

### 🎨 Skills System
- **Specialized agents**: Load domain-specific capabilities
- **Tool restriction**: Limit available tools per skill
- **Custom prompts**: Define behavior via Markdown files
- **Easy creation**: YAML frontmatter + instructions

### 🌐 Web Integration
- **Live search**: Access current information
- **Content extraction**: Parse and summarize web pages
- **Modular**: Ready for additional sources

### 👁️ Vision Capabilities
- **Multi-format**: JPEG, PNG, GIF, WebP support
- **Auto-optimization**: Resize images for efficiency
- **Multi-image**: Analyze multiple images simultaneously
- **Screenshot debugging**: Visual error analysis

### 🎭 Interactive Mode
- **Rich REPL**: Beautiful terminal interface
- **Streaming**: See responses as they arrive
- **History**: Command history and auto-suggestions
- **Slash commands**: `/help`, `/clear`, `/model`, etc.

---

## 📖 Documentation

### System Architecture

![BladeRunner Architecture](/ARCHITECTURE.png)

**Architecture Overview:**
- **Tier 1 Features** (green): Strategic thinking and resilience—Planning, Reflection, Retry, Streaming
- **Tier 2 Features** (orange): Safety and learning—Safety Detection, Approvals, Tool Tracking, Memory, Agent Selection
- **Tool Registry**: Extensible architecture supporting Bash, Read/Write, WebSearch, Image analysis, and custom tools
- **Storage Layer**: Persistent sessions, tool statistics, semantic memory, and configuration
- **API Clients**: Integration with OpenRouter, Groq, Brave Search, and external services

**Additional Documentation:**
- **[AGENTIC-AI.md](AGENTIC-AI.md)** - Complete agentic AI feature reference (Tier 1 + Tier 2)
- **[EXAMPLES.md](EXAMPLES.md)** - Copy-paste ready examples for all capabilities

---

## 🏗️ Architecture

**Project Structure:**

```
bladerunner/
├── cli.py              # Command-line interface
├── agent.py            # Core agent orchestration
├── config.py           # Configuration management
├── interactive.py      # REPL interface
├── permissions.py      # Security & access control
├── sessions.py         # Session persistence
├── skills.py           # Specialized capabilities
├── safety.py           # Critical operation detection (Tier 2)
├── tool_tracker.py     # Tool effectiveness tracking (Tier 2)
├── semantic_memory.py  # Solution memory and retrieval (Tier 2)
├── agent_orchestrator.py # Multi-agent task routing (Tier 2)
├── tools/              # Tool implementations
│   ├── base.py         # Tool base class & registry
│   ├── filesystem.py   # Read/Write operations
│   ├── bash.py         # Shell command execution
│   ├── web.py          # Web search & fetching
│   └── image.py        # Image analysis
```

## 🎯 Use Cases

### Development Automation
```bash
uv run bladerunner -p "Create a FastAPI project with auth, tests, and docs"
```

### Code Review
```bash
uv run bladerunner --skill code-reviewer -p "Review security issues in auth.py"
```

### Research & Implement
```bash
uv run bladerunner -p "Research OAuth2 PKCE flow and implement it"
```

### Multi-Session Projects
```bash
# Day 1: Foundation
uv run bladerunner --session webapp -p "Create Flask app structure"

# Day 2: Features
uv run bladerunner --continue -p "Add user authentication"

# Day 3: Testing
uv run bladerunner --continue -p "Write comprehensive tests"
```

### Visual Debugging
```bash
uv run bladerunner --image error.png -p "Explain this error and suggest fixes"
```

---

## ⚙️ Configuration

### Model Selection

BladeRunner supports two backends with different model offerings:

**OpenRouter Backend (default):**

| Model | Provider | Cost | Best For | Speed |
|-------|----------|------|----------|-------|
| **claude-haiku** | Anthropic | $0.25/1M tokens | Default (fast & capable) | ⚡⚡⚡ |
| **claude-sonnet** | Anthropic | $3/1M tokens | Complex reasoning | ⚡⚡ |
| **claude-opus** | Anthropic | $15/1M tokens | Most capable | ⚡ |
| **llama-3.1-8b** | Meta | **FREE** | Budget testing | ⚡⚡⚡ |
| **gemini-flash-1.5** | Google | **FREE** | Fast prototyping | ⚡⚡⚡ |
| **mistral-7b** | Mistral | **FREE** | Quick tasks | ⚡⚡ |

**Groq Backend (fast & free):**

| Model | Provider | Cost | Best For | Speed |
|-------|----------|------|----------|-------|
| **llama-3.1-70b** | Meta | **FREE** | General purpose | ⚡⚡⚡ FASTEST |
| **mixtral-8x7b** | Mistral | **FREE** | Complex tasks | ⚡⚡⚡ FASTEST |

**Using models:**

```bash
# OpenRouter models (default backend)
uv run bladerunner --model haiku -p "Your task"     # Claude (paid)
uv run bladerunner --model llama -p "Your task"     # Llama (free on OpenRouter)

# Groq models (set backend=groq in config)
uv run bladerunner --model groq-llama -p "Your task"   # Llama 70B (free, fastest!)
uv run bladerunner --model groq-mixtral -p "Your task" # Mixtral (free, fastest!)

# Or use full model names
uv run bladerunner --model meta-llama/llama-3.1-8b-instruct:free -p "Your task"
```

**Why Claude is default:**
- Superior tool-calling accuracy (critical for agents)
- Better at following complex multi-step instructions
- Strong safety and refusal handling
- Vision support for image analysis

**For learning/demos:** Use Groq backend (free, blazing fast)  
**For production agents:** Claude Haiku on OpenRouter (best accuracy/cost balance)

### Configuration File

Create `~/.bladerunner/config.yml`:

```yaml
# Backend selection
backend: openrouter  # openrouter or groq

# Model settings
model: haiku  # haiku, sonnet, or opus

# Security
permissions:
  enabled: true
  profile: standard  # strict, standard, permissive

# Sessions
sessions:
  enabled: true

# Web search (requires BRAVE_API_KEY)
web_search:
  enabled: true
  provider: brave
  max_results: 5

# Skills
skills:
  enabled: true
  directory: ~/.bladerunner/skills
```

### Web Search Alternatives

BladeRunner currently uses **Brave Search API** (2,000 free queries/month). Here are alternative providers:

| Provider | Best For | Cost | Setup Complexity |
|----------|----------|------|------------------|
| **Brave Search** | Portfolio, demos, privacy | Free tier (2K/mo) | ⭐ Easy |
| **Tavily AI** | AI agents, production | ~$0.002/search | ⭐⭐ Moderate |
| **Serper** | Budget-conscious, clean API | ~$0.001/search | ⭐ Easy |
| **Google Custom Search** | Accuracy, established projects | 100 free/day | ⭐⭐⭐ Complex |
| **SerpAPI** | Rapid prototyping | $$$ (starts at $50/mo) | ⭐ Easy |

**Why Brave for this project?**
- Free tier is generous for demos and learning
- Privacy-focused (good portfolio story)
- Simple authentication (just an API key)
- No complex OAuth or cloud provider setup

**For production agents:** Consider [Tavily AI](https://tavily.com) or [Serper](https://serper.dev) - they're optimized for LLM consumption and return cleaner, more structured results.

**To switch providers:** Modify `bladerunner/tools/web.py` to use your preferred API. The tool interface remains the same.

---

## 💡 Why This Matters

BladeRunner showcases:

1. **Agent Architecture**: Proper tool orchestration and state management
2. **Production Patterns**: Modular design, error handling, configuration
3. **Security**: Multi-tier permission system for autonomous agents
4. **Multimodal AI**: Integration of text and vision capabilities
5. **Real-world Features**: Session persistence, web search, interactive mode
6. **Code Quality**: Type hints, documentation, modular design

Perfect for demonstrating **Agentic AI** and **AI Engineer** capabilities.

**Built with ❤️ to demonstrate production-ready AI agent architecture**
