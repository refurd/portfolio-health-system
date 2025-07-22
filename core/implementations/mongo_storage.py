from pymongo import MongoClient
from bson import ObjectId
from typing import Dict, List, Optional, Any
from core.interfaces.storage import StorageInterface
import config

class MongoStorage(StorageInterface):
    def __init__(self):
        self.client = None
        self.db = None
        
    def connect(self):
        self.client = MongoClient(config.MONGO_CONNECTION_STRING)
        self.db = self.client[config.DATABASE_NAME]
        
    def disconnect(self):
        if self.client:
            self.client.close()
            
    def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        result = self.db[collection].insert_one(document)
        return str(result.inserted_id)
        
    def insert_many(self, collection: str, documents: List[Dict[str, Any]]) -> List[str]:
        result = self.db[collection].insert_many(documents)
        return [str(id) for id in result.inserted_ids]
        
    def find_one(self, collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.db[collection].find_one(query)
        
    def find(self, collection: str, query: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        cursor = self.db[collection].find(query)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)
        
    def update_one(self, collection: str, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        result = self.db[collection].update_one(query, {"$set": update})
        return result.modified_count > 0
        
    def delete_one(self, collection: str, query: Dict[str, Any]) -> bool:
        result = self.db[collection].delete_one(query)
        return result.deleted_count > 0