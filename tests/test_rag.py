from pathlib import Path

import pytest

from bladerunner.tools.rag import RAG_AVAILABLE

# Skip all tests if RAG dependencies are not installed
pytestmark = pytest.mark.skipif(
    not RAG_AVAILABLE,
    reason="RAG dependencies not installed (uv sync --extra rag)",
)


@pytest.fixture
def rag_store(tmp_path: Path):
    """Create a temporary RAG store for testing."""
    from bladerunner.tools.rag import RAGStore

    return RAGStore(persist_directory=tmp_path / "test_rag")


def test_add_and_search_documents(rag_store) -> None:
    """Test basic document ingestion and retrieval."""
    from bladerunner.tools.rag import RAGStore

    documents = [
        "Python is a high-level programming language",
        "JavaScript is used for web development",
        "Machine learning uses neural networks",
    ]

    # Add documents
    result = rag_store.add_documents(documents)
    assert result["status"] == "success"
    assert result["count"] == 3
    assert len(result["ids"]) == 3

    # Search for relevant documents
    search_result = rag_store.search("programming language", n_results=2)
    assert search_result["status"] == "success"
    assert search_result["count"] >= 1
    assert len(search_result["results"]) >= 1

    # Verify relevance - Python document should be most relevant
    top_result = search_result["results"][0]
    assert "Python" in top_result["document"]
    assert top_result["relevance_score"] > 0.3  # Semantic similarity threshold


def test_search_with_metadata_filtering(rag_store) -> None:
    """Test document search with metadata filters."""
    documents = [
        "FastAPI is a modern Python web framework",
        "Django is a batteries-included Python framework",
        "Express.js is a Node.js web framework",
    ]
    metadatas = [
        {"language": "python", "category": "web"},
        {"language": "python", "category": "web"},
        {"language": "javascript", "category": "web"},
    ]

    rag_store.add_documents(documents, metadatas=metadatas)

    # Search across all documents
    result_all = rag_store.search("web framework", n_results=3)
    assert result_all["count"] >= 2

    # Search with metadata filter (Python only)
    result_filtered = rag_store.search(
        "web framework", n_results=3, filter_dict={"language": "python"}
    )
    assert result_filtered["status"] == "success"
    # Should return Python frameworks only
    for res in result_filtered["results"]:
        assert res["metadata"].get("language") == "python"


def test_rag_ingest_tool(tmp_path: Path) -> None:
    """Test RAGIngestTool wrapper."""
    from bladerunner.tools.rag import RAGIngestTool, RAGStore

    rag_store = RAGStore(persist_directory=tmp_path / "tool_test")
    tool = RAGIngestTool(rag_store=rag_store)

    assert tool.name == "rag_ingest"
    assert "ingest" in tool.description.lower()
    assert "documents" in tool.parameters["properties"]

    # Execute ingestion
    documents = ["AI agents can reason and plan", "RAG improves LLM context"]
    result = tool.execute(documents=documents)

    assert "success" in result
    assert "count" in result or "2" in result  # JSON result contains count


def test_rag_search_tool(tmp_path: Path) -> None:
    """Test RAGSearchTool wrapper."""
    from bladerunner.tools.rag import RAGIngestTool, RAGSearchTool, RAGStore

    rag_store = RAGStore(persist_directory=tmp_path / "search_tool_test")

    # First ingest some documents
    ingest_tool = RAGIngestTool(rag_store=rag_store)
    documents = [
        "Vector embeddings enable semantic search",
        "ChromaDB is a vector database",
        "Sentence transformers generate embeddings",
    ]
    ingest_tool.execute(documents=documents)

    # Now test search tool
    search_tool = RAGSearchTool(rag_store=rag_store)

    assert search_tool.name == "rag_search"
    assert "search" in search_tool.description.lower()
    assert "query" in search_tool.parameters["properties"]

    # Execute search
    result = search_tool.execute(query="vector database", n_results=2)

    assert "success" in result or "results" in result
    assert "ChromaDB" in result  # Should find the relevant document


def test_persistence_across_sessions(tmp_path: Path) -> None:
    """Test that documents persist across RAGStore instances."""
    from bladerunner.tools.rag import RAGStore

    persist_dir = tmp_path / "persistent_rag"

    # First session: add documents
    store1 = RAGStore(persist_directory=persist_dir)
    documents = ["Persistent storage is important", "Vector databases save embeddings"]
    store1.add_documents(documents)

    # Second session: load from disk and search
    store2 = RAGStore(persist_directory=persist_dir)
    result = store2.search("persistent storage", n_results=1)

    assert result["status"] == "success"
    assert result["count"] >= 1
    assert "Persistent storage" in result["results"][0]["document"]


def test_empty_documents_handling(rag_store) -> None:
    """Test error handling for empty document list."""
    result = rag_store.add_documents([])
    assert result["status"] == "error"
    assert "No documents" in result["message"]
