from abc import ABC, abstractmethod
from typing import Dict, Any, List

class ValidatorInterface(ABC):
    @abstractmethod
    def validate(self, data: Dict[str, Any], validation_prompt: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def validate_batch(self, data_list: List[Dict[str, Any]], validation_prompt: str) -> List[Dict[str, Any]]:
        pass