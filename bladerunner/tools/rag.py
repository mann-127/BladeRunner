"""Retrieval-Augmented Generation (RAG) tools for document search and retrieval."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from .base import Tool

try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer

    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


class RAGStore:
    """Manages vector storage and retrieval for RAG."""

    def __init__(self, persist_directory: Optional[Path] = None):
        """Initialize RAG store with vector database."""
        if not RAG_AVAILABLE:
            raise ImportError(
                "RAG dependencies not installed. Install with: uv sync --extra rag"
            )

        self.persist_dir = persist_directory or (
            Path.home() / ".bladerunner" / "rag_store"
        )
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB with persistent storage
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Initialize embedding model (using a lightweight model)
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

        # Get or create default collection
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            metadata={"description": "General knowledge base for RAG"},
        )

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Add documents to the vector store.

        Args:
            documents: List of document texts to add
            metadatas: Optional list of metadata dicts for each document
            ids: Optional list of unique IDs for documents

        Returns:
            Dict with status and count of documents added
        """
        if not documents:
            return {"status": "error", "message": "No documents provided"}

        # Generate IDs if not provided
        if ids is None:
            import hashlib

            ids = [
                hashlib.md5(doc.encode()).hexdigest()[:16] for doc in documents
            ]

        # Generate embeddings
        embeddings = self.embedding_model.encode(documents).tolist()

        # Add to collection
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas or [{} for _ in documents],
            ids=ids,
        )

        return {
            "status": "success",
            "count": len(documents),
            "ids": ids,
        }

    def search(
        self, query: str, n_results: int = 5, filter_dict: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Search for relevant documents using semantic similarity.

        Args:
            query: Search query text
            n_results: Number of results to return
            filter_dict: Optional metadata filter

        Returns:
            Dict with search results and metadata
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()[0]

        # Search in collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_dict,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                formatted_results.append(
                    {
                        "document": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else None,
                        "relevance_score": 1 - (results["distances"][0][i] if results["distances"] else 0),
                    }
                )

        return {
            "status": "success",
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results),
        }

    def delete_collection(self, collection_name: str = "knowledge_base") -> Dict[str, Any]:
        """Delete a collection from the vector store."""
        try:
            self.client.delete_collection(name=collection_name)
            return {"status": "success", "message": f"Deleted collection: {collection_name}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_collections(self) -> List[str]:
        """List all collections in the vector store."""
        collections = self.client.list_collections()
        return [c.name for c in collections]


class RAGIngestTool(Tool):
    """Tool for ingesting documents into RAG vector store."""

    def __init__(self, rag_store: Optional[RAGStore] = None):
        """Initialize RAG ingest tool."""
        self.rag_store = rag_store or RAGStore()

    @property
    def name(self) -> str:
        return "rag_ingest"

    @property
    def description(self) -> str:
        return (
            "Ingest documents into the RAG knowledge base for later retrieval. "
            "Accepts a list of documents (text strings) and optional metadata. "
            "Documents are embedded and stored in a vector database for semantic search."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "documents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of document texts to ingest",
                },
                "metadatas": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Optional list of metadata objects for each document (e.g., source, timestamp)",
                },
            },
            "required": ["documents"],
        }

    def execute(self, documents: List[str], metadatas: Optional[List[Dict]] = None) -> str:
        """Execute document ingestion."""
        if not RAG_AVAILABLE:
            return "Error: RAG dependencies not installed. Install with: uv sync --extra rag"

        try:
            result = self.rag_store.add_documents(documents, metadatas)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error ingesting documents: {str(e)}"


class RAGSearchTool(Tool):
    """Tool for searching the RAG knowledge base."""

    def __init__(self, rag_store: Optional[RAGStore] = None):
        """Initialize RAG search tool."""
        self.rag_store = rag_store or RAGStore()

    @property
    def name(self) -> str:
        return "rag_search"

    @property
    def description(self) -> str:
        return (
            "Search the RAG knowledge base using semantic similarity. "
            "Returns the most relevant documents based on the query. "
            "Use this to retrieve context from previously ingested documents."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant documents",
                },
                "n_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    def execute(self, query: str, n_results: int = 5) -> str:
        """Execute semantic search."""
        if not RAG_AVAILABLE:
            return "Error: RAG dependencies not installed. Install with: uv sync --extra rag"

        try:
            result = self.rag_store.search(query, n_results)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error searching knowledge base: {str(e)}"
