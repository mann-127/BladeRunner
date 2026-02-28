"""Multi-agent orchestration for specialized agent roles."""

from typing import Dict, Any
from enum import Enum


class AgentRole(Enum):
    """Different agent roles with specialized capabilities."""

    GENERAL = "general"  # Default: handles all tasks
    CODE = "code"  # Specialized in code generation/analysis
    TEST = "test"  # Specialized in testing/debugging
    DOCS = "docs"  # Specialized in documentation
    ARCHITECT = "architect"  # Specialized in system design


class AgentSpecialization:
    """Specialization profile for agents."""

    def __init__(
        self,
        role: AgentRole,
        name: str,
        system_prompt_suffix: str,
        preferred_tools: list,
        description: str,
    ):
        """Initialize agent specialization."""
        self.role = role
        self.name = name
        self.system_prompt_suffix = system_prompt_suffix
        self.preferred_tools = preferred_tools
        self.description = description

    def enhance_system_prompt(self, base_prompt: str) -> str:
        """Enhance system prompt with specialization."""
        return f"{base_prompt}\n\n{self.system_prompt_suffix}"


class AgentOrchestrator:
    """Routes tasks to specialized agents."""

    def __init__(self):
        """Initialize orchestrator with agent specializations."""
        self.specializations = {
            AgentRole.GENERAL: AgentSpecialization(
                AgentRole.GENERAL,
                "General Assistant",
                (
                    "You are a general-purpose AI assistant. "
                    "Handle any task the user requests."
                ),
                ["Read", "Write", "Bash", "WebSearch"],
                "General purpose agent for any task",
            ),
            AgentRole.CODE: AgentSpecialization(
                AgentRole.CODE,
                "Code Specialist",
                (
                    "You are an expert code generation and refactoring agent. "
                    "Focus on writing clean, tested, maintainable code. "
                    "Always consider error handling, types, and best practices. "
                    "Prioritize code quality over quick solutions."
                ),
                ["Write", "Bash", "Read"],
                "Specialized in code generation and refactoring",
            ),
            AgentRole.TEST: AgentSpecialization(
                AgentRole.TEST,
                "Testing Specialist",
                (
                    "You are an expert in testing and debugging. "
                    "Write comprehensive tests, identify edge cases, and "
                    "debug problems. Focus on test coverage and reliability. "
                    "Always verify solutions work correctly."
                ),
                ["Bash", "Write", "Read"],
                "Specialized in testing and debugging",
            ),
            AgentRole.DOCS: AgentSpecialization(
                AgentRole.DOCS,
                "Documentation Specialist",
                (
                    "You are a documentation expert. "
                    "Write clear, comprehensive documentation with examples. "
                    "Explain complex concepts simply. "
                    "Include usage patterns and troubleshooting."
                ),
                ["Write", "Read", "WebSearch"],
                "Specialized in writing documentation",
            ),
            AgentRole.ARCHITECT: AgentSpecialization(
                AgentRole.ARCHITECT,
                "Architecture Specialist",
                (
                    "You are a system architect. "
                    "Design scalable, maintainable systems. "
                    "Consider tradeoffs, performance, and future evolution. "
                    "Think about data flow, separation of concerns, and APIs."
                ),
                ["Read", "Write", "WebSearch"],
                "Specialized in system design and architecture",
            ),
        }

    def select_agent(self, task: str) -> AgentRole:
        """Select best agent for task using keyword matching."""
        task_lower = task.lower()

        # Code-related keywords
        if any(
            kw in task_lower
            for kw in [
                "write",
                "code",
                "function",
                "class",
                "refactor",
                "implement",
                "generate",
                "script",
                "module",
            ]
        ):
            return AgentRole.CODE

        # Test-related keywords
        if any(
            kw in task_lower
            for kw in [
                "test",
                "debug",
                "fix",
                "bug",
                "error",
                "issue",
                "verify",
                "check",
            ]
        ):
            return AgentRole.TEST

        # Docs-related keywords
        if any(
            kw in task_lower
            for kw in [
                "document",
                "readme",
                "guide",
                "explain",
                "tutorial",
                "example",
                "comment",
            ]
        ):
            return AgentRole.DOCS

        # Architecture-related keywords
        if any(
            kw in task_lower
            for kw in [
                "design",
                "architecture",
                "system",
                "structure",
                "scalable",
                "plan",
                "organize",
            ]
        ):
            return AgentRole.ARCHITECT

        # Default to general
        return AgentRole.GENERAL

    def get_specialization(self, role: AgentRole) -> AgentSpecialization:
        """Get specialization details for a role."""
        return self.specializations.get(role, self.specializations[AgentRole.GENERAL])

    def route_task(self, task: str) -> Dict[str, Any]:
        """Route task to appropriate agent."""
        role = self.select_agent(task)
        specialization = self.get_specialization(role)

        return {
            "role": role,
            "agent_name": specialization.name,
            "system_prompt_suffix": specialization.system_prompt_suffix,
            "preferred_tools": specialization.preferred_tools,
            "description": specialization.description,
        }

    def print_agent_info(self, role: AgentRole) -> str:
        """Get info about an agent role."""
        spec = self.get_specialization(role)
        return f"[{spec.name}] {spec.description}"
