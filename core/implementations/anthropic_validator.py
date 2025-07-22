from anthropic import Anthropic
from typing import Dict, Any, List
from core.interfaces.validator import ValidatorInterface
import config
import json

class AnthropicValidator(ValidatorInterface):
    def __init__(self):
        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        
    def validate(self, data: Dict[str, Any], validation_prompt: str) -> Dict[str, Any]:
        prompt = f"{validation_prompt}\n\nData to validate:\n{json.dumps(data, indent=2)}"
        
        response = self.client.messages.create(
            model=config.VALIDATOR_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        try:
            return json.loads(response.content[0].text)
        except:
            return {"valid": False, "errors": ["Invalid response format"]}
            
    def validate_batch(self, data_list: List[Dict[str, Any]], validation_prompt: str) -> List[Dict[str, Any]]:
        results = []
        for data in data_list:
            results.append(self.validate(data, validation_prompt))
        return results