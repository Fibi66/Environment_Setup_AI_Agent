from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import hashlib
from ..core import LLMEngine, MemoryManager, SafetyController


class BaseAgent(ABC):
    def __init__(self, name: str, role: str, config):
        self.name = name
        self.role = role
        self.config = config
        self.llm = LLMEngine(config)
        self.memory = MemoryManager()
        self.safety = SafetyController(config)
    
    @abstractmethod
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def think(self, prompt: str, use_cache: bool = True) -> str:
        # Check cache if enabled
        if use_cache:
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
            cached = self.memory.get_cached_response(prompt_hash)
            if cached:
                return cached
        
        # Generate response
        response = await self.llm.generate(prompt)
        
        # Cache response
        if use_cache:
            self.memory.cache_llm_response(prompt_hash, response)
        
        return response
    
    async def think_json(self, prompt: str) -> Dict[str, Any]:
        return await self.llm.generate_json(prompt)
    
    def build_context(self, state: Dict[str, Any]) -> str:
        context_parts = [f"Current state: {self.name}"]
        
        # Add relevant state information
        for key, value in state.items():
            if value and key not in ['history', 'internal']:
                context_parts.append(f"{key}: {value}")
        
        # Add recent memory context
        recent_context = self.memory.get_context(limit=5)
        if recent_context:
            context_parts.append("\nRecent context:")
            for ctx in recent_context:
                context_parts.append(f"- {ctx['key']}: {ctx['value']}")
        
        return "\n".join(context_parts)
    
    def log(self, message: str, level: str = "info"):
        print(f"[{self.name}] {message}")
    
    async def validate_output(self, output: Any) -> bool:
        # Basic validation - can be overridden
        return output is not None