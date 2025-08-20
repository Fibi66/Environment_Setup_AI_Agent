import os
import json
from typing import Dict, Any, Optional, List, AsyncGenerator
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None
    
    def _get_client(self):
        if not self._client:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client
    
    async def generate(self, prompt: str, **kwargs) -> str:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            **kwargs
        )
        return response.choices[0].message.content
    
    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        client = self._get_client()
        stream = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            **kwargs
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None
    
    def _get_client(self):
        if not self._client:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client
    
    async def generate(self, prompt: str, **kwargs) -> str:
        client = self._get_client()
        response = await client.messages.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            **kwargs
        )
        return response.content[0].text
    
    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        client = self._get_client()
        async with client.messages.stream(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            **kwargs
        ) as stream:
            async for text in stream.text_stream:
                yield text


class LLMEngine:
    def __init__(self, config):
        self.config = config
        self.providers = {}
        self._init_providers()
    
    def _init_providers(self):
        # Initialize primary LLM
        primary_cfg = self.config.get_llm_config('primary')
        provider = self._create_provider(primary_cfg)
        if provider:
            self.providers['primary'] = provider
        
        # Initialize fast LLM for simple tasks
        if 'fast' in self.config.data.get('llm', {}):
            fast_cfg = self.config.get_llm_config('fast')
            provider = self._create_provider(fast_cfg)
            if provider:
                self.providers['fast'] = provider
    
    def _create_provider(self, cfg) -> Optional[LLMProvider]:
        if not cfg.api_key:
            return None
            
        if cfg.provider == 'openai':
            return OpenAIProvider(cfg.api_key, cfg.model, cfg.temperature, cfg.max_tokens)
        elif cfg.provider == 'anthropic':
            return AnthropicProvider(cfg.api_key, cfg.model, cfg.temperature, cfg.max_tokens)
        else:
            raise ValueError(f"Unknown provider: {cfg.provider}")
    
    def is_configured(self) -> bool:
        return len(self.providers) > 0
    
    async def generate(self, prompt: str, provider: str = 'primary', **kwargs) -> str:
        llm = self.providers.get(provider)
        if not llm:
            raise ValueError(f"LLM provider '{provider}' not configured. Please set API key.")
        return await llm.generate(prompt, **kwargs)
    
    async def stream(self, prompt: str, provider: str = 'primary', **kwargs) -> AsyncGenerator[str, None]:
        llm = self.providers.get(provider)
        if not llm:
            raise ValueError(f"LLM provider '{provider}' not configured. Please set API key.")
        async for chunk in llm.stream(prompt, **kwargs):
            yield chunk
    
    async def generate_json(self, prompt: str, provider: str = 'primary', **kwargs) -> Dict[str, Any]:
        # Add JSON instruction to prompt
        json_prompt = f"{prompt}\n\nRespond with valid JSON only."
        response = await self.generate(json_prompt, provider, **kwargs)
        
        # Extract JSON from response
        try:
            # Try to find JSON in the response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback: ask LLM to fix it
            fix_prompt = f"Convert this to valid JSON:\n{response}"
            fixed = await self.generate(fix_prompt, provider='fast' if 'fast' in self.providers else 'primary', **kwargs)
            return json.loads(fixed)