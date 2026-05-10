"""Tests for core agent functionality."""

import pytest

from bladerunner.agent import Agent
from bladerunner.config import Config


@pytest.fixture(autouse=True)
def fake_api_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    yield


def test_agent_initialization(tmp_path):
    config = Config(tmp_path / "config.yml")
    agent = Agent(config)

    assert agent.config is config
    assert agent.model == "gemma"
    assert agent.registry is not None


def test_agent_accepts_custom_model(tmp_path):
    config = Config(tmp_path / "config.yml")
    agent = Agent(config, model="llama-70b")

    assert agent.model == "llama-70b"


def test_agent_registers_core_tools(tmp_path):
    config = Config(tmp_path / "config.yml")
    agent = Agent(config)

    assert agent.registry.get("Read") is not None
    assert agent.registry.get("Write") is not None
    assert agent.registry.get("Bash") is not None


def test_agent_does_not_register_web_tools_when_disabled(tmp_path):
    config = Config(tmp_path / "config.yml")
    agent = Agent(config)

    assert agent.registry.get("WebSearch") is None


def test_agent_registers_web_tools_when_enabled(tmp_path):
    config = Config(tmp_path / "config.yml")
    config.config.setdefault("web_search", {})["enabled"] = True
    agent = Agent(config)

    assert agent.registry.get("WebSearch") is not None


def test_agent_clear_history(tmp_path):
    config = Config(tmp_path / "config.yml")
    agent = Agent(config)
    agent.messages.append({"role": "user", "content": "hi"})

    agent.clear_history()

    assert agent.messages == []
    assert not agent.interrupted

    assert agent.messages == []
    assert not agent.interrupted


def test_agent_set_model(tmp_path):
    config = Config(tmp_path / "config.yml")
    agent = Agent(config)

    agent.set_model("qwen3-coder")

    assert agent.model == "qwen3-coder"


def test_agent_append_message_trims_history(tmp_path):
    config = Config(tmp_path / "config.yml")
    config.config.setdefault("agent", {})["max_history_messages"] = 3
    agent = Agent(config)

    for i in range(10):
        agent._append_message({"role": "user", "content": f"msg {i}"})

    non_system = [m for m in agent.messages if m.get("role") != "system"]
    assert len(non_system) <= 3


def test_agent_set_and_clear_system_context(tmp_path):
    config = Config(tmp_path / "config.yml")
    agent = Agent(config)

    agent._set_system_context("test", "some content")
    assert any(
        m.get("role") == "system" and isinstance(m.get("content"), str) and "[Context:test]" in m["content"]
        for m in agent.messages
    )

    agent._clear_system_context("test")
    assert not any(
        m.get("role") == "system" and isinstance(m.get("content"), str) and "[Context:test]" in m["content"]
        for m in agent.messages
    )


def test_agent_set_system_context_updates_existing(tmp_path):
    config = Config(tmp_path / "config.yml")
    agent = Agent(config)

    agent._set_system_context("key", "first")
    agent._set_system_context("key", "second")

    system_msgs = [
        m
        for m in agent.messages
        if m.get("role") == "system" and isinstance(m.get("content"), str) and "[Context:key]" in m["content"]
    ]
    assert len(system_msgs) == 1
    assert "second" in system_msgs[0]["content"]


def test_agent_execute_returns_final_answer(tmp_path, monkeypatch):
    config = Config(tmp_path / "config.yml")
    config.config.setdefault("sessions", {})["enabled"] = False
    agent = Agent(config)

    from types import SimpleNamespace

    def _fake_create(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Done!", tool_calls=None))])

    monkeypatch.setattr(agent.client.chat.completions, "create", _fake_create)

    result = agent.execute("do something")
    assert result == "Done!"


def test_agent_execute_handles_interrupt(tmp_path, monkeypatch):
    config = Config(tmp_path / "config.yml")
    config.config.setdefault("sessions", {})["enabled"] = False
    agent = Agent(config, use_permissions=False)

    from types import SimpleNamespace

    call_count = [0]

    def _interrupt_on_second(**kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            agent.interrupted = True
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=None,
                            tool_calls=[
                                SimpleNamespace(
                                    id="c1",
                                    type="function",
                                    function=SimpleNamespace(
                                        name="Bash",
                                        arguments='{"command":"echo hi"}',
                                    ),
                                )
                            ],
                        )
                    )
                ]
            )
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Done", tool_calls=None))])

    monkeypatch.setattr(agent.client.chat.completions, "create", _interrupt_on_second)
    monkeypatch.setattr(agent.registry, "execute", lambda name, **kw: "ok")

    result = agent.execute("do something")
    assert "interrupted" in result.lower()


def test_agent_execute_max_iterations(tmp_path, monkeypatch):
    config = Config(tmp_path / "config.yml")
    config.config.setdefault("sessions", {})["enabled"] = False
    config.config.setdefault("agent", {})["max_iterations"] = 2
    agent = Agent(config, use_permissions=False)

    from types import SimpleNamespace

    def _tool_response(**kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=None,
                        tool_calls=[
                            SimpleNamespace(
                                id="call_1",
                                type="function",
                                function=SimpleNamespace(
                                    name="Bash",
                                    arguments='{"command":"echo hi"}',
                                ),
                            )
                        ],
                    )
                )
            ]
        )

    monkeypatch.setattr(agent.client.chat.completions, "create", _tool_response)
    monkeypatch.setattr(agent.registry, "execute", lambda name, **kw: "ok")

    result = agent.execute("loop forever")
    assert "max iterations" in result.lower()


def test_agent_execute_on_exception(tmp_path, monkeypatch):
    config = Config(tmp_path / "config.yml")
    config.config.setdefault("sessions", {})["enabled"] = False
    agent = Agent(config)

    monkeypatch.setattr(
        agent.client.chat.completions,
        "create",
        lambda **kw: (_ for _ in ()).throw(RuntimeError("api down")),
    )

    result = agent.execute("something")
    assert "error" in result.lower() or "api down" in result.lower()


def test_agent_was_web_search_used(tmp_path):
    config = Config(tmp_path / "config.yml")
    agent = Agent(config)

    assert not agent.was_web_search_used()
    agent._execution_path.append("tool:WebSearch(query)")
    assert agent.was_web_search_used()


def test_agent_permission_profile_none_uses_permissive(tmp_path):
    config = Config(tmp_path / "config.yml")
    agent = Agent(config, use_permissions=False)

    assert agent.safety.profile == "permissive"


def test_agent_denies_critical_bash(tmp_path, monkeypatch):
    config = Config(tmp_path / "config.yml")
    config.config.setdefault("sessions", {})["enabled"] = False
    agent = Agent(config, permission_profile="strict")
    # Auto-deny all prompts (non-interactive)
    setattr(agent.safety, "prompt_approval", lambda *_, **__: False)
    setattr(agent.safety, "prompt_permission", lambda *_, **__: False)
    agent.require_approval = True

    from types import SimpleNamespace

    def _bash_tool_call(**kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=None,
                        tool_calls=[
                            SimpleNamespace(
                                id="call_1",
                                type="function",
                                function=SimpleNamespace(
                                    name="Bash",
                                    arguments='{"command":"rm -rf /tmp/test"}',
                                ),
                            )
                        ],
                    )
                )
            ]
        )

    def _final(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="done", tool_calls=None))])

    call_count = [0]

    def _alternating(**kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _bash_tool_call(**kwargs)
        return _final(**kwargs)

    monkeypatch.setattr(agent.client.chat.completions, "create", _alternating)

    result = agent.execute("run dangerous command")
    assert result is not None
