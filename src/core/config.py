import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()


@dataclass
class LLMConfig:
    provider: str
    model: str
    temperature: float
    max_tokens: int
    api_key: Optional[str] = None
    endpoint: Optional[str] = None


@dataclass
class SafetyConfig:
    enabled: bool
    auto_approve_timeout: int
    critical_patterns: list
    auto_approve: list


class Config:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._default_config_path()
        self.data = self._load_config()
        
    def _default_config_path(self) -> str:
        return str(Path(__file__).parent.parent.parent / "configs" / "default.yaml")
    
    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Replace environment variables
        config = self._substitute_env_vars(config)
        return config
    
    def _substitute_env_vars(self, config: Any) -> Any:
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith('${') and config.endswith('}'):
            var_expr = config[2:-1]
            if ':-' in var_expr:
                var_name, default = var_expr.split(':-', 1)
                return os.getenv(var_name, default)
            return os.getenv(var_expr, config)
        return config
    
    def get_llm_config(self, profile: str = 'primary') -> LLMConfig:
        llm_cfg = self.data['llm'][profile]
        return LLMConfig(
            provider=llm_cfg['provider'],
            model=llm_cfg['model'],
            temperature=llm_cfg.get('temperature', 0.7),
            max_tokens=llm_cfg.get('max_tokens', 4000),
            api_key=os.getenv(f"{llm_cfg['provider'].upper()}_API_KEY"),
            endpoint=llm_cfg.get('endpoint')
        )
    
    def get_safety_config(self) -> SafetyConfig:
        safety_cfg = self.data['safety']
        return SafetyConfig(
            enabled=safety_cfg['hitl']['enabled'],
            auto_approve_timeout=safety_cfg['hitl']['auto_approve_timeout'],
            critical_patterns=safety_cfg['critical_patterns'],
            auto_approve=safety_cfg['auto_approve']
        )
    
    @property
    def execution(self) -> Dict[str, Any]:
        return self.data.get('execution', {})
    
    @property
    def reporting(self) -> Dict[str, Any]:
        return self.data.get('reporting', {})