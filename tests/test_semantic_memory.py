from pathlib import Path

from bladerunner.semantic_memory import SemanticMemory, SimpleTextSimilarity


def test_similarity_metrics() -> None:
    assert SimpleTextSimilarity.jaccard_similarity("test code", "code test") == 1.0
    assert SimpleTextSimilarity.token_overlap("alpha beta", "beta gamma") > 0


def test_store_and_find_similar_solutions(tmp_path: Path) -> None:
    memory = SemanticMemory(tmp_path)

    memory.store_solution(
        task_description="write python sorting function",
        execution_path=[
            "tool: Write implemented function",
            "tool: Bash ran tests",
        ],
        success=True,
    )
    memory.store_solution(
        task_description="failed operation",
        execution_path=["tool: Bash did something"],
        success=False,
    )

    assert len(memory.solutions) == 1

    similar = memory.find_similar_solutions(
        "python function for sorting", threshold=0.2
    )
    assert len(similar) == 1
    assert similar[0]["task"] == "write python sorting function"


def test_memory_context_and_clear(tmp_path: Path) -> None:
    memory = SemanticMemory(tmp_path)

    memory.store_solution(
        task_description="generate readme docs",
        execution_path=["tool: Write updated README", "tool: Read checked links"],
        success=True,
    )

    context = memory.get_memory_context("generate readme docs quickly")
    assert "[Similar Past Solutions]" in context
    assert "Tools:" in context

    memory.clear_memory()
    assert memory.solutions == []
    assert not (tmp_path / "solutions.jsonl").exists()
