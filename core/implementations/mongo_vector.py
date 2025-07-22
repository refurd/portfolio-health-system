from typing import List, Dict, Any, Tuple, Optional
from core.interfaces.vector_store import VectorStoreInterface
from core.implementations.mongo_storage import MongoStorage
from bson import ObjectId
import numpy as np

class MongoVectorStore(VectorStoreInterface):
    def __init__(self, storage: MongoStorage):
        self.storage = storage
        
    def create_index(self, collection: str, field: str, dimensions: int):
        # Create a 2dsphere index for vector similarity search
        self.storage.db[collection].create_index([(field, "2dsphere")])
        self.storage.db[collection].create_index([("embedding", 1)])
        
    def insert_vectors(self, collection: str, documents: List[Dict[str, Any]]):
        if documents:
            self.storage.insert_many(collection, documents)
        
    def search_similar(self, collection: str, query_vector: List[float], k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
        """Search for similar documents using cosine similarity"""
        try:
            # Get all documents with embeddings
            pipeline = [
                {"$match": {"embedding": {"$exists": True, "$ne": []}}},
                {"$limit": 1000}  # Limit to prevent memory issues
            ]
            
            documents = list(self.storage.db[collection].aggregate(pipeline))
            
            results = []
            query_vec = np.array(query_vector)
            
            for doc in documents:
                if 'embedding' in doc and doc['embedding']:
                    try:
                        doc_vec = np.array(doc['embedding'])
                        if doc_vec.shape == query_vec.shape:
                            similarity = self._cosine_similarity(query_vec, doc_vec)
                            results.append((doc, float(similarity)))
                    except Exception as e:
                        continue
                        
            # Sort by similarity descending
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:k]
            
        except Exception as e:
            print(f"Error in search_similar: {str(e)}")
            return []
        
    def update_vector(self, collection: str, document_id: str, vector: List[float]):
        try:
            if isinstance(document_id, str):
                doc_id = ObjectId(document_id)
            else:
                doc_id = document_id
                
            self.storage.update_one(
                collection, 
                {'_id': doc_id}, 
                {'embedding': vector}
            )
        except Exception as e:
            print(f"Error updating vector: {str(e)}")
        
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return dot_product / (norm1 * norm2)
        except Exception:
            return 0.0