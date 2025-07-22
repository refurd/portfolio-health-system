from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

class StorageInterface(ABC):
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def disconnect(self):
        pass
    
    @abstractmethod
    def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        pass
    
    @abstractmethod
    def insert_many(self, collection: str, documents: List[Dict[str, Any]]) -> List[str]:
        pass
    
    @abstractmethod
    def find_one(self, collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def find(self, collection: str, query: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def update_one(self, collection: str, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def delete_one(self, collection: str, query: Dict[str, Any]) -> bool:
        pass