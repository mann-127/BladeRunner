"""Shared text normalization utilities used by semantic_memory and skills."""

import re

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "is",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
        "task",
        "tasks",
        "thing",
        "things",
    }
)

SYNONYM_MAP = {
    "build": "create",
    "make": "create",
    "construct": "create",
    "generate": "create",
    "creates": "create",
    "building": "create",
}


def normalize_token(token):
    """Lowercase, stem, and synonym-map a single token."""
    token = token.lower().strip()
    if not token:
        return ""

    if token.endswith("ies") and len(token) > 4:
        token = token[:-3] + "y"
    elif token.endswith("ing") and len(token) > 5:
        token = token[:-3]
    elif token.endswith("ed") and len(token) > 4 or token.endswith("es") and len(token) > 4:
        token = token[:-2]
    elif token.endswith("s") and len(token) > 3:
        token = token[:-1]

    return SYNONYM_MAP.get(token, token)


def tokenize(text, min_length=1):
    """Tokenize *text* into a set of normalized, informative terms."""
    tokens = set()
    for raw in re.findall(r"[a-zA-Z0-9]+", text.lower()):
        if len(raw) < min_length:
            continue
        normalized = normalize_token(raw)
        if normalized and normalized not in STOPWORDS:
            tokens.add(normalized)
    return tokens
