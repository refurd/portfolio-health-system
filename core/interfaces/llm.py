from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class LLMInterface(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7) -> str:
        pass
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        pass
    
    @abstractmethod
    def batch_generate(self, prompts: List[str], system_prompt: Optional[str] = None) -> List[str]:
        pass