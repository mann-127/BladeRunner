"""Semantic memory — stores and recalls past successful solutions."""

import contextlib
import json
import logging
import math
from datetime import datetime
from pathlib import Path

from .text_utils import tokenize

logger = logging.getLogger(__name__)

try:
    import importlib

    _st_mod = importlib.import_module("sentence_transformers")
    SentenceTransformer = getattr(_st_mod, "SentenceTransformer")
    _EMBEDDINGS_AVAILABLE = True
except Exception:
    # sentence_transformers not available at runtime
    SentenceTransformer = None
    _EMBEDDINGS_AVAILABLE = False


def _jaccard(a, b):
    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


class Memory:
    """Persist successful task solutions and retrieve similar ones as context."""

    def __init__(self, data_dir=None, use_embeddings=False, embedding_model="all-MiniLM-L6-v2"):
        self.data_dir = data_dir or (Path.home() / ".bladerunner" / "memory")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._file = self.data_dir / "solutions.jsonl"
        self._solutions = self._load()
        self._encoder = None

        if use_embeddings:
            if not _EMBEDDINGS_AVAILABLE:
                logger.warning("sentence-transformers not installed; using lexical similarity")
            else:
                try:
                    self._encoder = SentenceTransformer(embedding_model)
                except Exception as e:
                    logger.warning("Failed to load embedding model: %s", e)

    def store(self, task, steps):
        """Persist a successful solution for future recall."""
        entry = {
            "task": task,
            "steps": steps,
            "timestamp": datetime.now().isoformat(),
        }
        self._solutions.append(entry)
        try:
            with open(self._file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error("Failed to persist memory: %s", e)

    def recall(self, task, threshold=0.3, limit=3):
        """Return a formatted context block of similar past solutions, or ''."""
        if not self._solutions:
            return ""
        scored = [(self._similarity(task, sol["task"]), sol) for sol in self._solutions]
        scored = [(s, sol) for s, sol in scored if s >= threshold]
        if not scored:
            return ""
        scored.sort(key=lambda x: x[0], reverse=True)
        lines = ["[Similar Past Solutions]"]
        for _, sol in scored[:limit]:
            lines.append(f"  Task: {sol['task']}")
            lines.append(f"  Steps: {' → '.join(sol['steps'])}")
        return "\n".join(lines)

    def clear(self):
        self._solutions.clear()
        with contextlib.suppress(Exception):
            self._file.unlink()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _similarity(self, a, b):
        if self._encoder is not None:
            try:
                vecs = self._encoder.encode([a, b])
                v1 = [float(x) for x in vecs[0]]
                v2 = [float(x) for x in vecs[1]]
                dot = sum(x * y for x, y in zip(v1, v2))
                n1 = math.sqrt(sum(x * x for x in v1))
                n2 = math.sqrt(sum(x * x for x in v2))
                if n1 and n2:
                    return max(0.0, min(1.0, dot / (n1 * n2)))
            except Exception:
                pass
        return _jaccard(a, b)

    def _load(self):
        if not self._file.exists():
            return []
        solutions = []
        try:
            with open(self._file) as f:
                for line in f:
                    if line.strip():
                        solutions.append(json.loads(line))
        except Exception as e:
            logger.warning("Failed to load memory: %s", e)
        return solutions
