from abc import ABC, abstractmethod


class BaseVectorRepository(ABC):
    """Interface for vector database operations."""

    @abstractmethod
    def ping(self):
        """Return True if backend is reachable."""

    @abstractmethod
    def collection_exists(self, collection_name):
        """Return True if collection exists."""

    @abstractmethod
    def create_collection(self, collection_name, vector_size):
        """Create a collection with vector params."""

    @abstractmethod
    def get_collection_stats(self, collection_name):
        """Return a normalized stats dictionary."""
