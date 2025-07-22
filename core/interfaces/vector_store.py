from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple

class VectorStoreInterface(ABC):
    @abstractmethod
    def create_index(self, collection: str, field: str, dimensions: int):
        pass
    
    @abstractmethod
    def insert_vectors(self, collection: str, documents: List[Dict[str, Any]]):
        pass
    
    @abstractmethod
    def search_similar(self, collection: str, query_vector: List[float], k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        pass
    
    @abstractmethod
    def update_vector(self, collection: str, document_id: str, vector: List[float]):
        pass