from abc import ABC, abstractmethod
from typing import List, Dict, Any


class VectorStore(ABC):
    """Abstract interface for vector storage backends."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the vector store."""
        ...

    @abstractmethod
    def create_collection(self, name: str, dim: int) -> None:
        """Create a collection with the given name and vector dimension."""
        ...

    @abstractmethod
    def insert(self, texts: List[str], vectors: List[List[float]],
               metadata: List[Dict[str, Any]]) -> None:
        """Insert texts with their embedding vectors and metadata."""
        ...

    @abstractmethod
    def search(self, query_vector: List[float], top_k: int,
               min_score: float) -> List[Dict[str, Any]]:
        """Search for similar vectors. Returns results with similarity scores in [0, 1]."""
        ...

    @abstractmethod
    def collection_exists(self, name: str) -> bool:
        """Check if a collection with the given name exists."""
        ...
