# BladeRunner Agentic AI Features

Complete reference for all agentic AI capabilities in BladeRunner.

---

## Overview

BladeRunner implements production-grade agentic AI features across strategic and safety layers:

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
- Performance Evaluation & Metrics
- Adaptive Strategy Guidance
- Structured Execution Tracing
- Capability Benchmark Runner

All features are optional and configurable.

---

## Design Principles

BladeRunner's agentic AI architecture is built on these core principles:

- **Modular features** with clear boundaries — each feature is independently configurable, allowing you to enable only what you need
- **Default safety** — permissions system and guarded commands protect against dangerous operations
- **Minimal configuration** — sensible defaults work out of the box with optional customization
- **Optional capabilities** — advanced features via optional dependencies keep the core lightweight
- **Deterministic, testable** tool behaviors — predictable execution for reliability and debugging

---

## Tier 1: Strategic Thinking & Resilience

### 1. Planning & Decomposition

**What it does:** Before executing, agent creates a multi-step plan.

**Impact:**
- Prevents wasted token calls on wrong approaches
- Better error handling and recovery
- Show agent's strategic thinking

**Configuration:**
```yaml
agent:
  enable_planning: true
```

**CLI:**
```bash
# Enable planning (default)
uv run bladerunner -p "Your task"

# Disable planning
uv run bladerunner -p "Your task" --no-planning
```

**Example flow:**
```
Prompt: "Analyze CSV and create dashboard"

[Plan]
1. Read CSV file and examine structure
2. Calculate statistics (mean, median, distribution)
3. Identify key insights (outliers, trends)
4. Generate HTML dashboard
5. Save and display
```

---

### 2. Reflection & Self-Correction

**What it does:** Agent analyzes tool output for errors and suggests fixes.

**Impact:**
- Self-aware error handling
- Better recovery strategies
- Learns from failures

**Configuration:**
```yaml
agent:
  enable_reflection: true
```

**CLI:**
```bash
# Disable reflection
uv run bladerunner -p "Your task" --no-reflection
```

**Example flow:**
```
Tool Error: "File not found: config.json"

[Reflecting on Read error]
The file might not exist or permissions denied.
Suggested approaches:
1. Check if file exists: ls -la config.json
2. Try reading with different encoding
3. Check file permissions
```

**Error Detection Keywords:**
- error, failed, traceback, exception
- not found, permission denied, invalid

---

### 3. Error Recovery & Retry

**What it does:** Intelligent retries with exponential backoff.

**Impact:**
- Handles transient failures
- Resilient execution
- Reduced hard failures

**Retry Configuration:**

| Tool | Max Retries | Backoff | Use Case |
|------|-------------|---------|----------|
| Bash | 3 | 2.0x | Complex commands |
| Read | 2 | 1.5x | File timing issues |
| Write | 2 | 1.5x | Disk/permission issues |
| WebSearch | 2 | 2.0x | Network timeouts |

**Backoff formula:** `wait_time = backoff_factor ^ attempt`

**Configuration:**
```yaml
agent:
  enable_retry: true
```

**CLI:**
```bash
# Disable retries
uv run bladerunner -p "Your task" --no-retry
```

**Example:**
```
Bash command failed
↓ Wait 1s, retry (attempt 2/3)
↓ Wait 2s, retry (attempt 3/3)
↓ Return error (all retries exhausted)
```

### Backend Fallback (OpenRouter <-> Groq)

**What it does:** When both backend API keys are configured, BladeRunner automatically switches to the next available backend on hard provider failures.

**Fallback triggers:**
- `429` rate limit errors
- `402` credit/payment errors
- repeated transient failures

**Cooldown behavior:**
- `429`: 120s cooldown
- `402`: 300s cooldown
- other errors: 60s cooldown

After cooldown, backends are retried automatically.

**Setup:**
```bash
OPENROUTER_API_KEY=your-openrouter-key
GROQ_API_KEY=your-groq-key
```

**Debug output:**
Set `debug: true` in config to see fallback events in stderr.

---

### FastAPI API Backend

**What it does:** Exposes BladeRunner through HTTP and WebSocket API endpoints.

**Endpoints:**
- `GET /api/health` - Service health + ADK/auth availability
- `GET /api/meta` - API metadata (models, skills, profiles)
- `GET /api/skills` - List configured skills
- `POST /api/auth/login` - JWT login (access + refresh tokens)
- `POST /api/auth/refresh` - JWT access token refresh
- `GET /api/auth/me` - Resolve current JWT identity
- `POST /api/sessions` - Create user session
- `GET /api/sessions` - List sessions by `user_id`
- `GET /api/sessions/{id}/messages` - Retrieve session messages
- `POST /api/uploads/image` - Upload image with per-user quota/type/size checks
- `GET /api/uploads/quota/{user_id}` - Inspect upload usage and remaining quota
- `POST /api/chat` - Chat completion (`bladerunner` or `google_adk` engine)
- `WS /ws/chat` - Bidirectional streaming (`chunk`, `status`, `final`, `interrupt`, `ping/pong`)

**Run:**
```bash
uv run bladerunner-api
```

**Configuration:**
```yaml
api:
  host: 127.0.0.1
  port: 8000
  database: ~/.bladerunner/api.db
  auth:
    enabled: false
    jwt:
      enabled: false
      secret_key: ""  # Set via BLADERUNNER_JWT_SECRET
  uploads:
    max_size_mb: 10
    per_user_quota_mb: 100
    retention_days: 30
```

---

### Google ADK / Gemini Grounding Engine

**What it does:** Adds a Google-first answer path for web-grounded responses in API mode.

**Behavior:**
- Checks for `google-adk` availability
- Uses Gemini grounded generation path
- Extracts source links from grounding metadata
- Returns answer + sources to API clients

**Setup:**
```bash
uv sync --extra google
export GOOGLE_API_KEY="your-key"
```

**Configuration:**
```yaml
google_adk:
  enabled: false
  model: gemini-2.0-flash
  enable_search_grounding: true
```

---

### 4. Streaming Responses

**What it does:** Stream tokens in real-time for responsive output.

**Impact:**
- Better perceived latency
- Real-time feedback
- Interactive feel

**Configuration:**
```yaml
agent:
  enable_streaming: false  # Default for CLI mode

interactive:
  streaming: true  # Default for interactive mode (enabled)
```

**Note:** Streaming is **ON by default** in interactive mode (`-i`), **OFF by default** in CLI mode.

**CLI:**
```bash
# Enable streaming in CLI mode
uv run bladerunner -p "Your task" --stream

# Interactive mode (streaming already enabled)
uv run bladerunner -i
```

---

## Tier 2: Safety & Learning

### 5. Human-in-the-Loop Approvals

**What it does:** Requires approval before critical operations.

**Critical Operations Detected:**
- Destructive bash: `rm -`, `dd`, `mkfs`, `fdisk`, `parted`
- Sensitive files: `/etc`, `/sys`, `~/.ssh`, `~/.aws`, `.env`
- Sensitive extensions: `.key`, `.pem`, `.p12`, `.pfx`

**Configuration:**
```yaml
agent:
  require_approval: true  # Enable (cannot disable - security feature)
```

**Example prompt:**
```
⚠️  CRITICAL OPERATION REQUIRES APPROVAL

Operation: Execute bash command
Reason: Delete files with 'rm' command
Details: rm -rf /old_data

Approve? (y)es / (n)o / (a)lways approve this pattern
> 
```

**User options:**
- `(y)` - Approve this specific operation
- `(n)` - Deny this specific operation
- `(a)` - Approve all matching operations (remembered for session)

---

### 6. Tool Effectiveness Tracking

**What it does:** Record tool success/failure rates and learn what works best.

**Tracks:**
- Total calls per tool
- Success/failure counts
- Success rate percentage
- Error types per tool
- Last usage timestamp

**Configuration:**
```yaml
agent:
  enable_tool_tracking: true
```

**Data storage:** `~/.bladerunner/metrics/tool_stats.json`

**Example output:**
```
📊 Tool Execution Summary (This Session):
--------------------------------------------------
  Bash: 2 calls, 2 success, 0 failed (100%)
  Read: 3 calls, 3 success, 0 failed (100%)
  Write: 1 calls, 1 success, 0 failed (100%)
--------------------------------------------------
  Total: 6 calls, 100% success rate

🏆 Tool Reliability Ranking (All Time):
--------------------------------------------------
  1. Read: 98% (49/50 calls)
  2. Write: 96% (24/25 calls)
  3. Bash: 88% (35/40 calls)
```

**Success Rate Thresholds:**
- ✅ ≥ 90%: Excellent (highly reliable)
- ⚠️ 70-89%: Fair (generally works)
- ❌ 50-69%: Poor (unreliable)
- ❌ < 50%: Failing (avoid using)

---

### 7. Semantic Memory (Learning)

**What it does:** Store successful solutions and retrieve similar past executions.

**Impact:**
- Agent learns from past solutions
- Reuses working strategies
- Builds knowledge base over time

**Configuration:**
```yaml
agent:
  enable_memory: true
```

**Data storage:** `~/.bladerunner/memory/solutions.jsonl`

**How it works:**
1. Store solution after successful execution
2. On new task, find similar past solutions
3. Inject past solutions as context
4. Agent references working strategies

**Example:**
```
Current task: "Create a database configuration file"

[Similar Past Solutions]
1. Task: Build PostgreSQL configuration
   Steps: Read template → Modify → Validate → Write
   Tools: Read, Write, Bash

2. Task: Set up environment config
   Steps: Create file → Add variables → Test → Finalize
   Tools: Write, Bash
```

**Similarity matching:**
- Algorithm: Jaccard similarity (word overlap)
- Threshold: 30% similarity required
- Returns: Top 3 most similar solutions

**Solution format:**
```json
{
  "task": "Create database config",
  "steps": ["tool:Read(file)", "tool:Write(file)", "tool:Bash(cmd)"],
  "timestamp": "2026-02-28T15:30:45",
  "tools_used": ["Read", "Write", "Bash"]
}
```

**Memory statistics:**
```
💾 Semantic Memory Statistics:
  Total solutions: 47
  Tools in memory:
    - Bash: 32 solutions
    - Write: 28 solutions
    - Read: 25 solutions
```

---

### 8. Multi-Agent Orchestration

**What it does:** Route tasks to specialized agents with different expertise.

**Agent Types:**

| Agent | Keywords | Specialization |
|-------|----------|-----------------|
| **Code** | write, code, function, implement, refactor | Code generation and quality |
| **Test** | test, debug, fix, bug, error, verify | Testing and debugging |
| **Docs** | document, guide, explain, tutorial | Documentation |
| **Architect** | design, architecture, system, structure | System design |
| **General** | (default) | Catch-all for any task |

**Configuration:**
```yaml
agent:
  enable_agent_selection: true
```

**Example output:**
```bash
$ uv run bladerunner -p "Write unit tests for login"

🤖 Testing Specialist

[Creating test suite...]
```

**How routing works:**
1. Parse user task description
2. Match against agent keywords
3. Select best matching agent
4. Enhance system prompt with specialization
5. Execute with agent's preferred tools

---

### 9. Performance Evaluation & Metrics

**What it does:** Tracks and analyzes agent performance across tasks.

**Metrics Tracked:**
- Task success/failure rates
- Iterations per task (efficiency)
- Token usage (total, prompt, completion)
- Tool usage patterns
- Execution duration
- Model performance comparison

**Configuration:**
```yaml
agent:
  enable_evaluation: true
```

**CLI:**
```bash
# Evaluation runs automatically in background
uv run bladerunner -p "Your task"

# View metrics summary (quick)
uv run python -c "from bladerunner.evaluation import AgentEvaluator; AgentEvaluator().print_summary()"

# Export metrics to JSON
uv run python -c "from bladerunner.evaluation import AgentEvaluator; import json; print(json.dumps(AgentEvaluator().get_summary(), indent=2))"

# View detailed execution history
uv run python -c "from bladerunner.evaluation import AgentEvaluator; ev=AgentEvaluator(); [print(ex.to_dict()) for ex in ev.executions_history[-5:]]"
```

**Programmatic Access:**
```python
from bladerunner.evaluation import AgentEvaluator

evaluator = AgentEvaluator()

# Get summary statistics
summary = evaluator.get_summary()
print(f"Success Rate: {summary['success_rate']*100:.1f}%")
print(f"Avg Duration: {summary['avg_duration_seconds']:.1f}s")
print(f"Total Tokens: {summary['total_tokens_used']:,}")

# Export metrics for external analysis
metrics_file = evaluator.export_metrics()  # Returns timestamped JSON file path
print(f"Metrics exported to: {metrics_file}")

# Access current execution
task_id = evaluator.start_task("Your task", model="haiku")
evaluator.record_tool_use("Bash")
evaluator.record_tokens(total=1523, prompt=823, completion=700)
evaluator.end_task(success=True)
```

**Example Output:**
```
============================================================
AGENT PERFORMANCE EVALUATION SUMMARY
============================================================

Last Updated: 2026-03-02T15:30:00

Total Tasks: 42
  ✓ Successful: 38
  ✗ Failed: 4
  Success Rate: 90.5%

Average Iterations per Task: 3.2
Average Duration: 12.5s

Total Tokens Used: 156,420
Average Tokens per Task: 3,724

Most Used Tools:
  - Bash: 89 times
  - Read: 67 times
  - Write: 45 times
  - WebSearch: 23 times

Model Performance:
  - haiku: 32 tasks (93.8% success)
  - sonnet: 10 tasks (80.0% success)
============================================================
```

**Why this matters:**
- **Identify bottlenecks**: Which tasks take longest?
- **Optimize costs**: Track token usage per model
- **Improve success rates**: Learn from failures
- **Compare models**: Which performs best for your workload?
- **Production readiness**: Essential for deployed agents

**Data Location:**
- Executions log: `~/.bladerunner/metrics/executions.jsonl`
- Summary: `~/.bladerunner/metrics/evaluation_summary.json`

**Export for Analysis:**
```python
from bladerunner.evaluation import AgentEvaluator

evaluator = AgentEvaluator()

# Export all metrics to timestamped JSON file
export_path = evaluator.export_metrics()
print(export_path)  # Prints: "Metrics exported to: ~/.bladerunner/metrics/export_1234567890.json"

# Export to specific file
evaluator.export_metrics(output_file="/path/to/metrics.json")

# Get recent executions
recent = evaluator.get_recent_executions(n=5)  # Last 5 tasks
for task in recent:
    print(f"Task: {task['prompt']}")
    print(f"Duration: {task.get('duration', 'N/A')}s")
    print(f"Success: {task['success']}")

# Clear all history (use with caution!)
# evaluator.clear_history()
```

**JSON Export Structure:**
```json
{
  "summary": {
    "last_updated": "2026-03-04T10:30:00",
    "total_tasks": 42,
    "success_rate": 0.905,
    "avg_duration_seconds": 12.5,
    "model_performance": {
      "haiku": {"total": 32, "successful": 30}
    }
  },
  "executions": [
    {
      "task_id": "task_1234567890",
      "prompt": "Your task",
      "duration": 15.2,
      "success": true,
      "tools_used": ["Bash", "Read", "Write"]
    }
  ]
}
```

---

### 10. Adaptive Strategy Guidance

**What it does:** Tracks repeated tool failures and injects bounded guidance so the agent avoids repeating a failing approach.

**When it triggers:** A tool exceeds a configurable consecutive-failure threshold.

**Configuration:**
```yaml
agent:
  enable_adaptation: true
  adaptation_failure_threshold: 2
```

**Behavior details:**
- Success resets consecutive failure count for that tool
- Failure streaks generate adaptive guidance messages
- Guidance is bounded and focused on strategy shift, not verbose replanning

**Why this matters:**
- Reduces retry loops that repeat the same failing arguments
- Improves robustness in flaky tool/network/file scenarios

---

### 11. Structured Execution Tracing

**What it does:** Records a structured event timeline for each execution (routing, planning, iterations, tool calls, completion/failure).

**Configuration:**
```yaml
agent:
  enable_trace: true
```

**Programmatic Access:**
```python
from bladerunner.agent import Agent
from bladerunner.config import Config

agent = Agent(Config())
agent.execute("Summarize README.md")
trace = agent.get_last_trace()
print(trace.get("status"))
print(len(trace.get("events", [])))
```

**API Access (`/api/chat` and `WS /ws/chat`):**
- Request field: `include_trace: true`
- Response field: `trace` (structured JSON trace payload)

**Why this matters:**
- Better post-mortem debugging for failed runs
- More transparent behavior for demos, audits, and evaluations

---

### 12. Capability Benchmark Runner

**What it does:** Runs declarative benchmark tasks and outputs category-level capability reports.

**Task packs included:**
- `software` (code understanding/execution)
- `data` (structured extraction/counting tasks)
- `research` (open-ended reasoning tasks with stronger checks)

**Run commands:**
```bash
# Run all benchmark packs
uv run bladerunner-eval --suite all

# Run one pack
uv run bladerunner-eval --suite software

# Limit task count for quick iteration
uv run bladerunner-eval --suite data --max-tasks 2
```

**Output:**
- JSON report written to `benchmarks/results/`
- Summary includes pass rate, per-category stats, median duration, and top failure reasons

**Why this matters:**
- Prevents regressions across releases
- Gives measurable capability snapshots instead of anecdotal demos

---

## RAG (Retrieval-Augmented Generation)

BladeRunner includes optional RAG capabilities for building and querying vector-based knowledge bases.

### Installation

```bash
uv sync --extra rag
```

**Dependencies:**
- ChromaDB: Persistent vector storage
- sentence-transformers: Embedding model (all-MiniLM-L6-v2)

### Configuration

```yaml
rag:
  enabled: true
  persist_directory: ~/.bladerunner/rag_store
  embedding_model: all-MiniLM-L6-v2
  default_collection: knowledge_base
```

### Available Tools

#### `rag_ingest`
Store documents in the vector database for later retrieval.

**Parameters:**
- `documents` (required): List of text strings to ingest
- `metadatas` (optional): List of metadata dicts for each document

**Example:**
```python
# Agent will use this tool when prompted
"Read docs/api.md and ingest it into the RAG knowledge base with metadata"
```

#### `rag_search`
Search the knowledge base using semantic similarity.

**Parameters:**
- `query` (required): Search query text
- `n_results` (optional): Number of results to return (default: 5)

**Example:**
```python
# Agent will use this tool when prompted
"Search the knowledge base for 'authentication patterns' and summarize the findings"
```

### How It Works

1. **Document ingestion**: Text is embedded using sentence-transformers
2. **Vector storage**: ChromaDB persists embeddings to disk
3. **Semantic search**: Query embeddings are compared to stored documents
4. **Relevance scoring**: Results ranked by cosine similarity

### Use Cases

- **Documentation retrieval**: Store and query internal wikis/docs
- **Code pattern discovery**: Find similar implementations
- **Customer support**: Knowledge base for FAQ responses
- **Compliance**: Search regulatory documents
- **Onboarding**: Contextual information for new developers

### Data Location

- Vector store: `~/.bladerunner/rag_store/`
- Collections: Managed via ChromaDB

### Limitations

- Embedding model is lightweight (384 dimensions) for performance
- No built-in document chunking (implement in prompts)
- Single collection support (can be extended)

---

## Configuration Reference

**For complete configuration options with all comments and settings**, see [config.example.yml](../config.example.yml).

### Quick Presets

**Default (Balanced):**
```yaml
agent:
  enable_planning: true
  enable_reflection: true
  enable_retry: true
  enable_streaming: false
  require_approval: true
  enable_tool_tracking: true
  enable_memory: true
  enable_agent_selection: true
```

**Fast Mode (Minimum Overhead):** Disable planning, reflection, and learning features
```yaml
agent:
  enable_planning: false
  enable_reflection: false
  enable_retry: true
  enable_streaming: false
  require_approval: false
  enable_tool_tracking: false
  enable_memory: false
  enable_agent_selection: false
```

**Production Mode (Maximum Safety):** All features enabled with strict approvals

---

## CLI Reference

### Feature Toggles

```bash
# Plan before executing
uv run bladerunner -p "task"

# Disable planning
uv run bladerunner -p "task" --no-planning

# Disable reflection on errors
uv run bladerunner -p "task" --no-reflection

# Disable automatic retries
uv run bladerunner -p "task" --no-retry

# Stream response tokens
uv run bladerunner -p "task" --stream

# Combine flags
uv run bladerunner -p "task" --stream --no-planning --no-reflection
```

### Feature Combinations

```bash
# Full agentic AI (all features enabled)
uv run bladerunner -p "task"

# Fast execution (no planning/reflection)
uv run bladerunner -p "task" --no-planning --no-reflection

# Safe mode (with streaming)
uv run bladerunner -p "task" --stream

# Learning mode (with tracking and memory)
uv run bladerunner -p "task"  # All enabled by default
```

---

## Performance Implications

### Token Usage

| Feature | Cost | Benefit |
|---------|------|---------|
| Planning | +100-200 tokens | Saves 5-10x tokens on approach decisions |
| Reflection | +50-150 per error | Improves recovery strategies |
| Retry | 0 tokens | Uses wait time (exponential backoff) |
| Streaming | 0 tokens | Just output formatting |
| Approvals | Interactive (no tokens) | Prevents catastrophes |
| Tool Tracking | Local logging only | Guides future decisions |
| Memory | +50-100 per similar solution | Saves 5-10x on similar tasks |
| Agent Selection | ~100 tokens | Better output quality |

### Execution Time

- **Fastest:** Disable Tier 1 + Tier 2
- **Balanced:** Keep Tier 1 + Tool Tracking, disable others
- **Safest:** All Tier 1 + All Tier 2

---

## Troubleshooting

### Approval prompts too frequent

**Solution:** Use "(a)lways" option when prompted to approve pattern.

### Tool success rates don't match experience

**Solution:** Clear statistics: `rm ~/.bladerunner/metrics/tool_stats.json`

### Memory contains irrelevant solutions

**Solution:** Clear memory: `rm ~/.bladerunner/memory/solutions.jsonl`

### Wrong agent selected

**Solution:** 
- Make task description more specific
- Or disable agent selection: `enable_agent_selection: false`

---

## Advanced Usage

### Programmatic Control

```python
from bladerunner.agent import Agent
from bladerunner.config import Config

agent = Agent(Config())

# Toggle features
agent.enable_planning = False
agent.enable_memory = False
agent.require_approval = False

result = agent.execute("Your task")

# Print metrics
print(agent.tool_tracker.get_reliability_ranking())
agent.semantic_memory.print_memory_stats()
agent.print_execution_summary()
```

### Accessing Metrics

```python
# Tool effectiveness
agent.tool_tracker.get_success_rate("Bash")
agent.tool_tracker.get_reliability_ranking()
agent.tool_tracker.get_tool_health()

# Recommendations
print(agent.tool_tracker.get_recommendation())

# Memory stats
agent.semantic_memory.print_memory_stats()

# Find similar solutions
similar = agent.semantic_memory.find_similar_solutions("your task")
```

---

## Interview Talking Points

This implementation demonstrates:

| Feature | What It Shows | Interview Value |
|---------|---------------|-----------------|
| Planning | Goal decomposition, strategic thinking | ⭐⭐⭐⭐ |
| Reflection | Self-awareness, error analysis | ⭐⭐⭐⭐ |
| Retry | Resilience engineering, exponential backoff | ⭐⭐⭐⭐ |
| Streaming | Real-time systems, async patterns | ⭐⭐⭐ |
| Approvals | Security engineering, safety-first design | ⭐⭐⭐⭐⭐ |
| Tool Tracking | ML/metrics thinking, observability | ⭐⭐⭐⭐ |
| Memory | Learning systems, NLP, knowledge graphs | ⭐⭐⭐⭐⭐ |
| Multi-Agent | System architecture, specialization, routing | ⭐⭐⭐⭐⭐ |

**Combined:** Production-grade agentic AI system with enterprise-level thinking

---

## File Reference

**New modules:**
- `bladerunner/safety.py` - Critical operation detection and approval
- `bladerunner/tool_tracker.py` - Effectiveness tracking and metrics
- `bladerunner/semantic_memory.py` - Solution storage and retrieval
- `bladerunner/agent_orchestrator.py` - Task routing to specialized agents

**Modified:**
- `bladerunner/agent.py` - Integrated all Tier 1 + Tier 2 features
- `bladerunner/config.py` - Added feature configuration defaults

**Data directories:**
- `~/.bladerunner/metrics/` - Tool effectiveness statistics
- `~/.bladerunner/memory/` - Semantic memory solutions
- `~/.bladerunner/sessions/` - Conversation history

---

## See Also

- [README.md](../README.md)
