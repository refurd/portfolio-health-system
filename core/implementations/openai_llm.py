from openai import OpenAI
from typing import List, Dict, Any, Optional
from core.interfaces.llm import LLMInterface
import config
import json
import time

class OpenAILLM(LLMInterface):
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=4000
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise e
        
    def generate_embedding(self, text: str) -> List[float]:
        if not text or not text.strip():
            return []
            
        # Truncate text if too long (max 8191 tokens)
        text = text[:8000]
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=config.EMBEDDING_MODEL,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"Error generating embedding: {str(e)}")
                    return []
        
    def batch_generate(self, prompts: List[str], system_prompt: Optional[str] = None) -> List[str]:
        results = []
        for prompt in prompts:
            try:
                result = self.generate(prompt, system_prompt)
                results.append(result)
            except Exception as e:
                print(f"Error in batch generate: {str(e)}")
                results.append("")
        return results