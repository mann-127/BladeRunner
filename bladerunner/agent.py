"""BladeRunner agent — core agentic loop."""

import contextlib
import json
import logging
import os
from types import SimpleNamespace

from openai import OpenAI

from .memory import Memory
from .safety import PermissionLevel, Safety
from .sessions import SessionManager
from .tools.base import ToolRegistry
from .tools.bash import BashTool
from .tools.filesystem import ReadTool, WriteTool

try:
    from .tools.web import FetchWebpageTool, WebSearchTool

    _WEB_AVAILABLE = True
except ImportError:
    _WEB_AVAILABLE = False

try:
    from .tools.image import ReadImageTool

    _IMAGE_AVAILABLE = True
except ImportError:
    _IMAGE_AVAILABLE = False

try:
    from .tools.rag import RAGIngestTool, RAGSearchTool, RAGStore

    _RAG_AVAILABLE = True
except ImportError:
    _RAG_AVAILABLE = False

logger = logging.getLogger(__name__)

_ERROR_KEYWORDS = (
    "error",
    "failed",
    "traceback",
    "exception",
    "not found",
    "permission denied",
)


class _StreamMessage:
    def __init__(self, content, tool_calls):
        self.content = content
        self.tool_calls = tool_calls or None


class Agent:
    """BladeRunner agent — prompt → LLM + tool calls loop → final answer."""

    def __init__(self, config, model=None, use_permissions=True, permission_profile=None, session_id=None):
        self.config = config
        self.model = model or config.get("model", "gemma")

        # LLM client
        backend = config.get("backend", "openrouter")
        backends = config.get("backends") or {}
        backend_cfg = backends.get(backend, {})
        api_key_env = backend_cfg.get("api_key_env", "OPENROUTER_API_KEY")
        api_key = config.get("api_key") or os.getenv(api_key_env)
        if not api_key:
            raise RuntimeError(f"{api_key_env} environment variable not set. Set it or add 'api_key' to your config.")
        base_url = backend_cfg.get("base_url", "https://openrouter.ai/api/v1")
        self.client = OpenAI(api_key=api_key, base_url=base_url)

        # Tools
        self.registry = ToolRegistry()
        self.registry.register(ReadTool())
        self.registry.register(WriteTool())
        self.registry.register(BashTool())
        if _WEB_AVAILABLE and config.get("web_search.enabled"):
            self.registry.register(
                WebSearchTool(
                    provider=config.get("web_search.provider", "duckduckgo"),
                    max_results=config.get("web_search.max_results", 5),
                )
            )
            self.registry.register(FetchWebpageTool())
        if _IMAGE_AVAILABLE:
            self.registry.register(ReadImageTool())
        if _RAG_AVAILABLE and config.get("rag.enabled", False):
            rag_store = RAGStore()
            self.registry.register(RAGIngestTool(rag_store))
            self.registry.register(RAGSearchTool(rag_store))

        # Safety
        profile = permission_profile or config.get("agent.permissions_profile", "standard")
        self.safety = Safety(profile=profile if use_permissions else "permissive")
        self.require_approval = config.get("agent.require_approval", True)

        # Session
        self.session_manager = None
        self.session_id = None
        if config.get("sessions.enabled", True):
            self.session_manager = SessionManager(config.get("sessions.directory"))
            if session_id:
                self.session_id = session_id

        # Memory
        self.memory = None
        if config.get("agent.memory_enabled", True):
            self.memory = Memory(
                use_embeddings=config.get("agent.memory_use_embeddings", False),
                embedding_model=config.get("agent.memory_embedding_model", "all-MiniLM-L6-v2"),
            )

        self.messages = []
        self.stream_callback = None
        self.interrupted = False

        self._tool_failures = {}
        self._execution_path = []
        self._max_iterations = int(config.get("agent.max_iterations", 30))
        self._max_history = int(config.get("agent.max_history_messages", 20))

        # Keep legacy attributes so existing api_server.py code still works
        # during the transition — these will be removed when api.py replaces it.
        self.enable_planning = False
        self.enable_reflection = False
        self.enable_retry = True
        self.enable_streaming = bool(config.get("agent.stream", False))

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def execute(self, prompt, use_streaming=False):
        """Run the agentic loop and return the final answer."""
        self._tool_failures.clear()
        self._execution_path.clear()
        self.interrupted = False

        if self.memory:
            ctx = self.memory.recall(prompt)
            if ctx:
                self._set_system_context("memory", ctx)

        self._append_message({"role": "user", "content": prompt})
        self._save_message(self.messages[-1])

        stream = use_streaming or self.enable_streaming
        model_settings = self.config.get_model_settings(self.model)

        for _ in range(self._max_iterations):
            if self.interrupted:
                return "\n⚠️ Task interrupted"
            try:
                if stream:
                    stream_response = self.client.chat.completions.create(
                        model=self.config.resolve_model(self.model),
                        messages=self.messages,
                        tools=self.registry.get_definitions(),
                        temperature=model_settings["temperature"],
                        max_tokens=model_settings["max_tokens"],
                        stream=True,
                    )
                    message = self._handle_stream(stream_response)
                else:
                    completion_response = self.client.chat.completions.create(
                        model=self.config.resolve_model(self.model),
                        messages=self.messages,
                        tools=self.registry.get_definitions(),
                        temperature=model_settings["temperature"],
                        max_tokens=model_settings["max_tokens"],
                        stream=False,
                    )
                    api_message = completion_response.choices[0].message
                    message = _StreamMessage(
                        content=api_message.content or "",
                        tool_calls=api_message.tool_calls,
                    )
            except KeyboardInterrupt:
                return "\nInterrupted by user"
            except Exception as e:
                return f"Error: {e}"

            assistant_msg = {
                "role": "assistant",
                "content": message.content,
            }
            tool_calls = self._normalize_tool_calls(message.tool_calls)
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            self._append_message(assistant_msg)
            self._save_message(assistant_msg)

            if tool_calls:
                for tc in tool_calls:
                    result = self._execute_tool(tc)
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": self._attr(tc, "id"),
                        "content": result,
                    }
                    self._append_message(tool_msg)
                    self._save_message(tool_msg)
            else:
                answer = message.content or ""
                if self.memory and self._execution_path:
                    self.memory.store(prompt, self._execution_path)
                self._clear_system_context("memory")
                return answer

        return f"Warning: Reached max iterations ({self._max_iterations})"

    def load_session(self, session_id):
        if self.session_manager:
            self.session_id = session_id
            self.messages = self.session_manager.load_session(session_id)

    def clear_history(self):
        self.messages.clear()
        self._tool_failures.clear()
        self._execution_path.clear()
        self.interrupted = False

    def set_model(self, model):
        self.model = model

    def was_web_search_used(self):
        return any("tool:WebSearch" in step for step in self._execution_path)

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def _execute_tool(self, tool_call):
        name = self._attr(tool_call, "function", "name")
        raw_args = self._attr(tool_call, "function", "arguments")
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON arguments: {e}"

        # Critical-operation checks (require explicit user approval)
        if self.require_approval:
            if name == "Bash":
                cmd = args.get("command", "")
                is_crit, reason = self.safety.is_critical_bash(cmd)
                if is_crit and not self.safety.prompt_approval("Execute bash", reason or "", cmd):
                    return "Error: Operation denied by user"
            elif name == "Write":
                path = args.get("file_path", "")
                is_crit, reason = self.safety.is_critical_write(path)
                if is_crit and not self.safety.prompt_approval("Write to critical file", reason or "", path):
                    return "Error: Operation denied by user"

        # Profile-based permission checks
        if name in ("Read", "ReadImage"):
            path = args.get("file_path") or args.get("image_path", "")
            if path:
                perm = self.safety.check_file_read(path)
                if perm == PermissionLevel.DENY:
                    return f"Error: Permission denied to read '{path}'"
                if perm == PermissionLevel.ASK and not self.safety.prompt_permission("Read file", path):
                    return f"Error: User denied read of '{path}'"
                if self.require_approval:
                    is_sensitive, reason = self.safety.is_critical_read(path)
                    if is_sensitive and not self.safety.prompt_approval("Read sensitive file", reason or "", path):
                        return f"Error: User denied read of '{path}'"
        elif name == "Write":
            path = args.get("file_path", "")
            if path:
                perm = self.safety.check_file_write(path)
                if perm == PermissionLevel.DENY:
                    return f"Error: Permission denied to write '{path}'"
                if perm == PermissionLevel.ASK and not self.safety.prompt_permission("Write file", path):
                    return f"Error: User denied write to '{path}'"
        elif name == "Bash":
            cmd = args.get("command", "")
            if cmd:
                perm = self.safety.check_bash(cmd)
                if perm == PermissionLevel.DENY:
                    return f"Error: Permission denied: {cmd}"
                if perm == PermissionLevel.ASK and not self.safety.prompt_permission("Execute command", cmd):
                    return f"Error: User denied command: {cmd}"

        try:
            result = self.registry.execute(name, **args)
        except Exception as e:
            result = f"Error executing {name}: {e}"

        # Consecutive failure guard — inject a hint after 3 failures
        is_error = any(kw in result.lower() for kw in _ERROR_KEYWORDS)
        if is_error:
            self._tool_failures[name] = self._tool_failures.get(name, 0) + 1
            if self._tool_failures[name] >= 3:
                self._set_system_context(
                    "hint",
                    f"[Note] {name} has failed "
                    f"{self._tool_failures[name]} consecutive times. "
                    "Try a different approach.",
                )
        else:
            self._tool_failures.pop(name, None)
            self._clear_system_context("hint")

        self._execution_path.append(f"tool:{name}({', '.join(args.keys())})")
        return result

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    def _handle_stream(self, stream):
        content = ""
        merged = {}

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                content += delta.content
                if self.stream_callback:
                    with contextlib.suppress(Exception):
                        self.stream_callback(delta.content)
                else:
                    print(delta.content, end="", flush=True)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = getattr(tc, "index", len(merged))
                    m = merged.setdefault(
                        idx,
                        {"id": "", "type": "function", "name": "", "arguments": ""},
                    )
                    if tc_id := self._attr(tc, "id"):
                        m["id"] = tc_id
                    if name_d := self._attr(tc, "function", "name"):
                        m["name"] += name_d
                    if args_d := self._attr(tc, "function", "arguments"):
                        m["arguments"] += args_d

        if content and not self.stream_callback:
            print()

        tool_calls = [
            SimpleNamespace(
                id=m["id"] or f"call_{i}",
                type=m["type"],
                function=SimpleNamespace(name=m["name"], arguments=m["arguments"]),
            )
            for i, m in sorted(merged.items())
        ]
        return _StreamMessage(content, tool_calls)

    # ------------------------------------------------------------------
    # Message helpers
    # ------------------------------------------------------------------

    def _normalize_tool_calls(self, tool_calls):
        if not tool_calls:
            return []
        return [
            {
                "id": self._attr(tc, "id") or f"call_{i}",
                "type": "function",
                "function": {
                    "name": self._attr(tc, "function", "name"),
                    "arguments": self._attr(tc, "function", "arguments"),
                },
            }
            for i, tc in enumerate(tool_calls)
        ]

    def _attr(self, obj, *keys):
        val = obj
        for key in keys:
            val = val.get(key, "") if isinstance(val, dict) else getattr(val, key, "")
        return str(val) if val is not None else ""

    def _append_message(self, message):
        self.messages.append(message)
        non_system = [i for i, m in enumerate(self.messages) if m.get("role") != "system"]
        excess = len(non_system) - self._max_history
        if excess > 0:
            to_drop = set(non_system[:excess])
            self.messages = [m for i, m in enumerate(self.messages) if i not in to_drop]

    def _save_message(self, message):
        if self.session_manager and self.session_id:
            self.session_manager.save_message(self.session_id, message)

    def _set_system_context(self, key, content):
        marker = f"[Context:{key}]"
        tagged = f"{marker}\n{content}"
        for msg in self.messages:
            if (
                msg.get("role") == "system"
                and isinstance(msg.get("content"), str)
                and msg["content"].startswith(marker)
            ):
                msg["content"] = tagged
                return
        self.messages.append({"role": "system", "content": tagged})

    def _clear_system_context(self, key):
        marker = f"[Context:{key}]"
        self.messages = [
            m
            for m in self.messages
            if not (m.get("role") == "system" and isinstance(m.get("content"), str) and m["content"].startswith(marker))
        ]

    # Legacy shim used by api_server.py during transition
    def get_last_trace(self):
        return {}
