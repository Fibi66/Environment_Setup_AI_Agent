import json
import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class MemoryManager:
    def __init__(self, base_path: str = "data/memory"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.short_term = {}  # Current session memory
        self.long_term_path = self.base_path / "long_term.json"
        self.cache_path = self.base_path / "cache"
        self.cache_path.mkdir(exist_ok=True)
        
        self._load_long_term()
    
    def _load_long_term(self):
        if self.long_term_path.exists():
            with open(self.long_term_path, 'r') as f:
                self.long_term = json.load(f)
        else:
            self.long_term = {}
    
    def save_long_term(self):
        with open(self.long_term_path, 'w') as f:
            json.dump(self.long_term, f, indent=2, default=str)
    
    def remember(self, key: str, value: Any, persistent: bool = False):
        self.short_term[key] = {
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
        
        if persistent:
            self.long_term[key] = self.short_term[key]
            self.save_long_term()
    
    def recall(self, key: str) -> Optional[Any]:
        # Check short-term first
        if key in self.short_term:
            return self.short_term[key]['value']
        
        # Then check long-term
        if key in self.long_term:
            return self.long_term[key]['value']
        
        return None
    
    def get_context(self, limit: int = 10) -> List[Dict[str, Any]]:
        # Get recent context from short-term memory
        items = sorted(
            self.short_term.items(),
            key=lambda x: x[1]['timestamp'],
            reverse=True
        )[:limit]
        
        return [{'key': k, **v} for k, v in items]
    
    def cache_llm_response(self, prompt_hash: str, response: str):
        cache_file = self.cache_path / f"{prompt_hash}.pkl"
        with open(cache_file, 'wb') as f:
            pickle.dump({
                'response': response,
                'timestamp': datetime.now().isoformat()
            }, f)
    
    def get_cached_response(self, prompt_hash: str) -> Optional[str]:
        cache_file = self.cache_path / f"{prompt_hash}.pkl"
        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
                return data['response']
        return None
    
    def add_project_learning(self, project_type: str, learnings: Dict[str, Any]):
        if 'project_patterns' not in self.long_term:
            self.long_term['project_patterns'] = {}
        
        if project_type not in self.long_term['project_patterns']:
            self.long_term['project_patterns'][project_type] = []
        
        self.long_term['project_patterns'][project_type].append({
            'learnings': learnings,
            'timestamp': datetime.now().isoformat()
        })
        
        self.save_long_term()
    
    def get_similar_projects(self, project_type: str) -> List[Dict[str, Any]]:
        if 'project_patterns' in self.long_term:
            return self.long_term['project_patterns'].get(project_type, [])
        return []