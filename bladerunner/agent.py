"""Main agent implementation."""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional
from openai import OpenAI

from .config import Config
from .safety import CriticalOperation
from .tool_tracker import ToolTracker
from .semantic_memory import SemanticMemory
from .agent_orchestrator import AgentOrchestrator, AgentRole
from .evaluation import AgentEvaluator
from .tools.base import ToolRegistry
from .tools.filesystem import ReadTool, WriteTool
from .tools.bash import BashTool
from .permissions import PermissionChecker, PermissionLevel
from .sessions import SessionManager

# Import optional tools
try:
    from .tools.web import WebSearchTool, FetchWebpageTool

    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False

try:
    from .tools.image import ReadImageTool

    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False

try:
    from .tools.rag import RAGIngestTool, RAGSearchTool, RAGStore

    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


MAX_ITERATIONS = 50

# Reflection thresholds
REFLECTION_KEYWORDS = [
    "error",
    "failed",
    "traceback",
    "exception",
    "not found",
    "permission denied",
    "invalid",
]

# Retry configuration
RETRY_CONFIG = {
    "Bash": {"max_retries": 3, "backoff_factor": 2},
    "Read": {"max_retries": 2, "backoff_factor": 1.5},
    "Write": {"max_retries": 2, "backoff_factor": 1.5},
    "WebSearch": {"max_retries": 2, "backoff_factor": 2},
}


class Agent:
    """Main BladeRunner agent."""

    def __init__(
        self,
        config: Config,
        model: Optional[str] = None,
        use_permissions: bool = True,
        permission_profile: str = "standard",
        session_id: Optional[str] = None,
    ):
        self.config = config
        self.model = model or config.get("model", "haiku")
        self.backend = config.get("backend", "openrouter")

        # Initialize API client with backend-specific settings
        api_key = config.get("api_key") or self._get_api_key_for_backend()
        base_url = self._get_base_url()
        self.client = OpenAI(api_key=api_key, base_url=base_url)

        # Initialize tool registry
        self.registry = ToolRegistry()
        self._register_core_tools()

        # Initialize optional features
        if WEB_AVAILABLE and config.get("web_search.enabled"):
            self._register_web_tools()

        if IMAGE_AVAILABLE:
            self._register_image_tools()

        if RAG_AVAILABLE and config.get("rag.enabled", False):
            self._register_rag_tools()

        # Permissions
        self.use_permissions = use_permissions and config.get(
            "permissions.enabled", True
        )
        if self.use_permissions:
            self.permission_checker = PermissionChecker(profile=permission_profile)
        else:
            self.permission_checker = None

        # Session management
        self.session_manager = None
        self.session_id = None
        if config.get("sessions.enabled", True):
            sessions_dir = config.get("sessions.directory")
            self.session_manager = SessionManager(sessions_dir)
            if session_id:
                self.session_id = session_id

        # Conversation state
        self.messages: List[Dict[str, Any]] = []

        # Agentic AI features
        self.enable_planning = config.get("agent.enable_planning", True)
        self.enable_reflection = config.get("agent.enable_reflection", True)
        self.enable_retry = config.get("agent.enable_retry", True)
        self.enable_streaming = config.get("agent.enable_streaming", False)

        # Track execution state for reflection
        self.last_tool_output = ""
        self.execution_history = []

        # Tier 2: Safety and approval system
        self.critical_checker = CriticalOperation()
        self.require_approval = config.get("agent.require_approval", True)

        # Tier 2: Tool effectiveness tracking
        self.tool_tracker = ToolTracker()
        self.enable_tool_tracking = config.get("agent.enable_tool_tracking", True)

        # Tier 2: Semantic memory (learning from past solutions)
        self.semantic_memory = SemanticMemory()
        self.enable_memory = config.get("agent.enable_memory", True)

        # Tier 2: Multi-agent orchestration
        self.orchestrator = AgentOrchestrator()
        self.agent_role = AgentRole.GENERAL
        self.enable_agent_selection = config.get("agent.enable_agent_selection", True)

        # Track execution path for memory storage
        self.current_execution_path: List[str] = []

        # Tier 2: Evaluation and metrics tracking
        self.evaluator = AgentEvaluator()
        self.enable_evaluation = config.get("agent.enable_evaluation", True)
        self.current_task_id: Optional[str] = None

    def _get_base_url(self) -> str:
        """Get base URL for the selected backend."""
        backends = self.config.get("backends", {})
        backend_config = backends.get(self.backend, {})
        return backend_config.get("base_url", "https://openrouter.ai/api/v1")

    def _get_api_key_for_backend(self) -> str:
        """Get API key from environment based on backend."""
        backends = self.config.get("backends", {})
        backend_config = backends.get(self.backend, {})
        env_var = backend_config.get("api_key_env", "OPENROUTER_API_KEY")

        api_key = os.getenv(env_var)
        if not api_key:
            raise RuntimeError(
                f"{env_var} environment variable not set for {self.backend} backend"
            )
        return api_key

    def _register_core_tools(self):
        """Register core tools."""
        self.registry.register(ReadTool())
        self.registry.register(WriteTool())
        self.registry.register(BashTool())

    def _register_web_tools(self):
        """Register web-related tools."""
        self.registry.register(WebSearchTool())
        self.registry.register(FetchWebpageTool())

    def _register_image_tools(self):
        """Register image-related tools."""
        self.registry.register(ReadImageTool())

    def _register_rag_tools(self):
        """Register RAG tools for vector storage and retrieval."""
        rag_store = RAGStore()
        self.registry.register(RAGIngestTool(rag_store))
        self.registry.register(RAGSearchTool(rag_store))

    def load_session(self, session_id: str):
        """Load messages from a session."""
        if self.session_manager:
            self.session_id = session_id
            self.messages = self.session_manager.load_session(session_id)

    def _create_plan(self, prompt: str) -> str:
        """Create a multi-step plan before execution."""
        if not self.enable_planning:
            return ""

        planning_prompt = f"""Create a concise step-by-step plan.

Task: {prompt}

Respond with a brief numbered plan (3-5 steps). Be concise."""

        plan_messages = self.messages.copy()
        plan_messages.append({"role": "user", "content": planning_prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.config.resolve_model(self.model),
                messages=plan_messages,
                temperature=0.3,  # Lower temp for plans
                max_tokens=500,
            )

            if response.choices and response.choices[0].message.content:
                plan = response.choices[0].message.content
                # Store plan in execution history
                self.execution_history.append(
                    {
                        "type": "plan",
                        "content": plan,
                        "timestamp": time.time(),
                    }
                )
                return plan
        except Exception as e:
            print(f"Warning: Failed to create plan: {str(e)}", file=sys.stderr)

        return ""

    def _should_reflect_on_output(self, output: str) -> bool:
        """Check if output indicates error that needs reflection."""
        if not self.enable_reflection:
            return False

        output_lower = output.lower()
        return any(keyword in output_lower for keyword in REFLECTION_KEYWORDS)

    def _reflect_on_execution(
        self, tool_name: str, output: str, arguments: Dict[str, Any]
    ) -> str:
        """Reflect on tool execution and suggest correction if needed."""
        if not self.enable_reflection or not self._should_reflect_on_output(output):
            return ""

        reflection_prompt = f"""Tool error or unexpected result:

Tool: {tool_name}
Arguments: {json.dumps(arguments, indent=2)}
Output: {output}

Analyze the error. Should we:
1. Retry with different arguments?
2. Try a different approach?
3. Ask user for clarification?

Be concise and actionable."""

        reflection_messages = self.messages.copy()
        reflection_messages.append({"role": "user", "content": reflection_prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.config.resolve_model(self.model),
                messages=reflection_messages,
                temperature=0.5,
                max_tokens=300,
            )

            if response.choices and response.choices[0].message.content:
                reflection = response.choices[0].message.content
                self.execution_history.append(
                    {
                        "type": "reflection",
                        "tool": tool_name,
                        "content": reflection,
                        "timestamp": time.time(),
                    }
                )
                return reflection
        except Exception as e:
            print(f"Warning: Reflection failed: {str(e)}", file=sys.stderr)

        return ""

    def _execute_tool_with_retry(self, tool_call) -> str:
        """Execute tool with retry logic and exponential backoff."""
        function_name = tool_call.function.name

        if not self.enable_retry:
            return self._execute_tool_with_permissions(tool_call)

        # Get retry config for this tool
        retry_config = RETRY_CONFIG.get(
            function_name, {"max_retries": 1, "backoff_factor": 1}
        )
        max_retries = retry_config["max_retries"]
        backoff_factor = retry_config["backoff_factor"]

        last_error = None

        for attempt in range(max_retries):
            try:
                result = self._execute_tool_with_permissions(tool_call)

                # If successful, return
                if not self._should_reflect_on_output(result):
                    self.last_tool_output = result
                    return result

                # If error, reflect and potentially retry
                last_error = result
                reflection = self._reflect_on_execution(
                    function_name,
                    result,
                    json.loads(tool_call.function.arguments),
                )

                if reflection:
                    # Add reflection to conversation for agent awareness
                    reflection_msg = (
                        f"[Reflecting on {function_name} error]\n{reflection}"
                    )
                    self.messages.append(
                        {
                            "role": "assistant",
                            "content": reflection_msg,
                        }
                    )

                # Exponential backoff before retry
                if attempt < max_retries - 1:
                    wait_time = backoff_factor**attempt
                    msg = (
                        f"Retrying {function_name} "
                        f"(attempt {attempt + 2}/{max_retries}) "
                        f"after {wait_time:.1f}s..."
                    )
                    print(msg, file=sys.stderr)
                    time.sleep(wait_time)

            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    wait_time = backoff_factor**attempt
                    time.sleep(wait_time)

        # All retries exhausted
        self.last_tool_output = last_error or "Tool execution failed after retries"
        return self.last_tool_output

    def execute(self, prompt: str, use_streaming: bool = False) -> str:
        """Execute agent with a prompt."""
        # Tier 2: Start evaluation tracking
        if self.enable_evaluation:
            self.current_task_id = self.evaluator.start_task(prompt, self.model)

        # Tier 2: Agent role selection
        if self.enable_agent_selection:
            route = self.orchestrator.route_task(prompt)
            self.agent_role = route["role"]
            print(f"🤖 {route['agent_name']}", file=sys.stderr)

        # Tier 2: Get semantic memory context
        memory_context = ""
        if self.enable_memory:
            memory_context = self.semantic_memory.get_memory_context(prompt)

        # Reset execution path tracker
        self.current_execution_path = []

        # Create plan if enabled
        plan = self._create_plan(prompt) if self.enable_planning else ""
        if plan:
            # Add plan to messages for context
            self.messages.append(
                {
                    "role": "assistant",
                    "content": f"[Plan]\n{plan}",
                }
            )

        # Add memory context if available
        if memory_context:
            self.messages.append(
                {
                    "role": "assistant",
                    "content": memory_context,
                }
            )

        # Add user message
        self.messages.append({"role": "user", "content": prompt})

        # Save to session if enabled
        if self.session_manager and self.session_id:
            self.session_manager.save_message(self.session_id, self.messages[-1])

        # Agent loop
        for iteration in range(MAX_ITERATIONS):
            try:
                # Record iteration for evaluation
                if self.enable_evaluation:
                    self.evaluator.record_iteration()

                # Get model response
                stream = use_streaming or self.enable_streaming
                response = self.client.chat.completions.create(
                    model=self.config.resolve_model(self.model),
                    messages=self.messages,
                    tools=self.registry.get_definitions(),
                    stream=stream,
                )

                if stream:
                    message = self._handle_streaming_response(response)
                else:
                    if not response.choices:
                        return "Error: No response from model"
                    message = response.choices[0].message

                # Add assistant message
                assistant_msg = {
                    "role": "assistant",
                    "content": message.content,
                }
                if message.tool_calls:
                    assistant_msg["tool_calls"] = message.tool_calls

                self.messages.append(assistant_msg)

                if self.session_manager and self.session_id:
                    self.session_manager.save_message(self.session_id, assistant_msg)

                # Check for tool calls
                if message.tool_calls:
                    # Execute tools with retry logic
                    for tool_call in message.tool_calls:
                        result = self._execute_tool_with_retry(tool_call)

                        tool_msg = {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        }
                        self.messages.append(tool_msg)

                        if self.session_manager and self.session_id:
                            self.session_manager.save_message(self.session_id, tool_msg)
                else:
                    # No tool calls - return final response
                    final_response = message.content or ""

                    # Tier 2: Store successful solution in semantic memory
                    if self.enable_memory and self.current_execution_path:
                        self.semantic_memory.store_solution(
                            prompt,
                            self.current_execution_path,
                            success=True,
                        )

                    # Tier 2: End evaluation tracking (success)
                    if self.enable_evaluation:
                        self.evaluator.end_task(success=True)

                    return final_response

            except KeyboardInterrupt:
                if self.enable_evaluation:
                    self.evaluator.end_task(
                        success=False, error_message="Interrupted by user"
                    )
                return "\nInterrupted by user"
            except Exception as e:
                if self.enable_evaluation:
                    self.evaluator.end_task(success=False, error_message=str(e))
                return f"Error: {str(e)}"

        # Max iterations reached
        if self.enable_evaluation:
            self.evaluator.end_task(
                success=False, error_message="Max iterations reached"
            )
        return f"Warning: Reached max iterations ({MAX_ITERATIONS})"

    def _handle_streaming_response(self, stream) -> Any:
        """Handle streaming response from API."""
        content = ""
        tool_calls = []

        for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Stream text content
            if delta.content:
                content += delta.content
                print(delta.content, end="", flush=True)

            # Handle tool calls in streaming
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    tool_calls.append(tool_call)

        if content:
            print()  # Newline after streaming

        # Create a message-like object
        class Message:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls if tool_calls else None

        return Message(content, tool_calls)

    def _execute_tool_with_permissions(self, tool_call) -> str:
        """Execute tool with permission and critical operation checks."""
        function_name = tool_call.function.name

        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON arguments: {str(e)}"

        print(
            f"Executing tool: {function_name} with args: {arguments}", file=sys.stderr
        )

        # Tier 2: Check for critical operations requiring approval
        if self.require_approval:
            if function_name == "Bash":
                command = arguments.get("command", "")
                is_critical, reason = self.critical_checker.is_critical_bash(command)
                if is_critical:
                    approved = self.critical_checker.prompt_approval(
                        "Execute bash command",
                        reason,
                        command,
                    )
                    if not approved:
                        return "Error: Critical operation denied by user"

            elif function_name == "Write":
                file_path = arguments.get("file_path", "")
                is_critical, reason = self.critical_checker.is_critical_file_write(
                    file_path
                )
                if is_critical:
                    approved = self.critical_checker.prompt_approval(
                        "Write to critical file",
                        reason,
                        file_path,
                    )
                    if not approved:
                        return "Error: Critical file write denied by user"

        # Permission checks
        if self.use_permissions and self.permission_checker:
            if function_name in ["Read", "ReadImage"]:
                file_path = arguments.get("file_path") or arguments.get("image_path")
                if file_path:
                    perm = self.permission_checker.check_file_read(file_path)
                    if perm == PermissionLevel.DENY:
                        return f"Error: Permission denied to read '{file_path}'"
                    elif perm == PermissionLevel.ASK:
                        if not self.permission_checker.prompt_user(
                            "Read file", file_path
                        ):
                            return (
                                f"Error: User denied permission to read '{file_path}'"
                            )

            elif function_name == "Write":
                file_path = arguments.get("file_path")
                if file_path:
                    perm = self.permission_checker.check_file_write(file_path)
                    if perm == PermissionLevel.DENY:
                        return f"Error: Permission denied to write '{file_path}'"
                    elif perm == PermissionLevel.ASK:
                        if not self.permission_checker.prompt_user(
                            "Write file", file_path
                        ):
                            return (
                                f"Error: User denied permission to write '{file_path}'"
                            )

            elif function_name == "Bash":
                command = arguments.get("command")
                if command:
                    perm = self.permission_checker.check_bash_command(command)
                    if perm == PermissionLevel.DENY:
                        return f"Error: Permission denied to execute command: {command}"
                    elif perm == PermissionLevel.ASK:
                        if not self.permission_checker.prompt_user(
                            "Execute command", command
                        ):
                            return (
                                f"Error: User denied permission to execute: {command}"
                            )

        # Execute tool and track effectiveness
        try:
            result = self.registry.execute(function_name, **arguments)

            # Tier 2: Track tool success
            if self.enable_tool_tracking:
                success = not result.startswith("Error:")
                self.tool_tracker.record_execution(
                    function_name, success, result if not success else None
                )

            # Tier 2: Track tool usage in evaluator
            if self.enable_evaluation:
                self.evaluator.record_tool_use(function_name)

            # Store execution step for memory
            step = f"tool:{function_name}({', '.join(arguments.keys())})"
            self.current_execution_path.append(step)

            return result

        except Exception as e:
            # Track tool failure
            if self.enable_tool_tracking:
                self.tool_tracker.record_execution(function_name, False, str(e))

            return f"Error executing {function_name}: {str(e)}"

    def clear_history(self):
        """Clear conversation history."""
        self.messages.clear()
        self.execution_history.clear()
        self.last_tool_output = ""

    def set_model(self, model: str):
        """Switch to a different model."""
        self.model = model

    def print_execution_summary(self) -> None:
        """Print summary of execution including Tier 2 stats."""
        print("\n" + "=" * 60)
        print("EXECUTION SUMMARY")
        print("=" * 60)

        # Tier 2: Evaluation metrics
        if self.enable_evaluation:
            self.evaluator.print_summary()

        # Tier 2: Tool tracking stats
        if self.enable_tool_tracking:
            self.tool_tracker.print_session_summary()
            self.tool_tracker.print_tool_rankings()

        # Tier 2: Semantic memory stats
        if self.enable_memory:
            self.semantic_memory.print_memory_stats()

        print()
