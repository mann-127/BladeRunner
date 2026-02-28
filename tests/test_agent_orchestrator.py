import pytest

from bladerunner.agent_orchestrator import AgentOrchestrator, AgentRole


@pytest.mark.parametrize(
    ("task", "expected_role"),
    [
        ("write a new module", AgentRole.CODE),
        ("debug failing tests", AgentRole.TEST),
        ("document setup steps", AgentRole.DOCS),
        ("design architecture for scale", AgentRole.ARCHITECT),
        ("what is the weather", AgentRole.GENERAL),
    ],
)
def test_select_agent(task: str, expected_role: AgentRole) -> None:
    orchestrator = AgentOrchestrator()

    assert orchestrator.select_agent(task) is expected_role


def test_route_task_includes_specialization_metadata() -> None:
    orchestrator = AgentOrchestrator()

    route = orchestrator.route_task("write robust python code")

    assert route["role"] is AgentRole.CODE
    assert route["agent_name"]
    assert isinstance(route["preferred_tools"], list)
    assert route["description"]


def test_print_agent_info_is_human_readable() -> None:
    orchestrator = AgentOrchestrator()

    info = orchestrator.print_agent_info(AgentRole.TEST)

    assert info.startswith("[")
    assert "Testing Specialist" in info
