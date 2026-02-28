"""Semantic memory for storing and retrieving past solutions."""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class SimpleTextSimilarity:
    """Simple string similarity without embeddings (no dependencies)."""

    @staticmethod
    def jaccard_similarity(str1: str, str2: str) -> float:
        """Calculate Jaccard similarity between two strings."""
        # Split into words
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def token_overlap(str1: str, str2: str) -> float:
        """Calculate token overlap (jaccard) between strings."""
        return SimpleTextSimilarity.jaccard_similarity(str1, str2)


class SemanticMemory:
    """Store and retrieve past execution solutions."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize semantic memory."""
        self.data_dir = data_dir or (Path.home() / ".bladerunner" / "memory")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.data_dir / "solutions.jsonl"

        self.solutions: List[Dict[str, Any]] = self._load_solutions()
        self.similarity = SimpleTextSimilarity()

    def _load_solutions(self) -> List[Dict[str, Any]]:
        """Load past solutions from file."""
        if not self.memory_file.exists():
            return []

        solutions = []
        try:
            with open(self.memory_file, "r") as f:
                for line in f:
                    if line.strip():
                        solutions.append(json.loads(line))
        except Exception:
            pass

        return solutions

    def store_solution(
        self, task_description: str, execution_path: List[str], success: bool
    ) -> None:
        """Store a successful task execution."""
        if not success:
            return  # Only store successful solutions

        solution = {
            "task": task_description,
            "steps": execution_path,
            "timestamp": datetime.now().isoformat(),
            "tools_used": self._extract_tools(execution_path),
        }

        self.solutions.append(solution)
        self._persist_solution(solution)

    def find_similar_solutions(
        self, task_description: str, threshold: float = 0.3, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Find similar past solutions."""
        if not self.solutions:
            return []

        similarities = []

        for solution in self.solutions:
            similarity = self.similarity.token_overlap(
                task_description, solution["task"]
            )

            if similarity >= threshold:
                similarities.append({"solution": solution, "similarity": similarity})

        # Sort by similarity descending
        similarities.sort(key=lambda x: x["similarity"], reverse=True)

        return [item["solution"] for item in similarities[:limit]]

    def get_memory_context(self, task_description: str) -> str:
        """Get formatted context from similar past solutions."""
        similar = self.find_similar_solutions(task_description)

        if not similar:
            return ""

        context = "\n[Similar Past Solutions]\n"

        for i, solution in enumerate(similar, 1):
            context += f"{i}. Task: {solution['task']}\n"
            context += f"   Steps: {' → '.join(solution['steps'])}\n"
            context += f"   Tools: {', '.join(solution['tools_used'])}\n\n"

        return context

    def _extract_tools(self, execution_path: List[str]) -> List[str]:
        """Extract tool names from execution path."""
        tools = set()
        for step in execution_path:
            # Extract tool name from step description
            if "tool:" in step.lower():
                tool = step.split("tool:")[1].strip().split()[0]
                tools.add(tool)
        return list(tools)

    def _persist_solution(self, solution: Dict[str, Any]) -> None:
        """Save solution to disk."""
        try:
            with open(self.memory_file, "a") as f:
                f.write(json.dumps(solution) + "\n")
        except Exception:
            pass  # Silently fail - don't break agent for memory

    def clear_memory(self) -> None:
        """Clear all stored solutions."""
        self.solutions.clear()
        try:
            self.memory_file.unlink()
        except Exception:
            pass

    def print_memory_stats(self) -> None:
        """Print memory statistics."""
        if not self.solutions:
            print("No solutions stored in semantic memory yet.")
            return

        print("\n💾 Semantic Memory Statistics:")
        print("-" * 50)
        print(f"  Total solutions: {len(self.solutions)}")

        # Group by tools used
        tool_counts: Dict[str, int] = {}
        for solution in self.solutions:
            for tool in solution.get("tools_used", []):
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

        if tool_counts:
            print("  Tools in memory:")
            sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)
            for tool, count in sorted_tools:
                print(f"    - {tool}: {count} solutions")
