import os
import json
from pathlib import Path
from typing import Dict, Any, List
from .base import BaseAgent
from ..tools import FileSystem, GitTools


class ScannerAgent(BaseAgent):
    def __init__(self, config):
        super().__init__("Scanner", "Project Analysis", config)
        self.fs = FileSystem()
        self.git = GitTools()
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("🔍 Scanning project structure...")
        
        project_path = state.get('project_path', '.')
        
        # Gather project information
        files = self.fs.scan_directory(project_path)
        config_files = self._find_config_files(files)
        
        # Build analysis prompt
        prompt = self._build_scan_prompt(project_path, files, config_files)
        
        # Get LLM analysis
        analysis = await self.think_json(prompt)
        
        # Update state
        state['scan_results'] = analysis
        state['detected_stacks'] = analysis.get('technology_stacks', [])
        state['project_type'] = analysis.get('project_type', 'unknown')
        state['dependencies'] = analysis.get('dependencies', {})
        
        self.memory.remember('scan_results', analysis, persistent=True)
        
        self.log(f"✅ Detected {len(state['detected_stacks'])} technology stacks")
        
        return state
    
    def _find_config_files(self, files: List[str]) -> Dict[str, str]:
        config_patterns = {
            'package.json': 'nodejs',
            'requirements.txt': 'python-pip',
            'Pipfile': 'python-pipenv',
            'pyproject.toml': 'python-poetry',
            'pom.xml': 'java-maven',
            'build.gradle': 'java-gradle',
            'Gemfile': 'ruby',
            'go.mod': 'golang',
            'Cargo.toml': 'rust',
            'docker-compose.yml': 'docker',
            'Dockerfile': 'docker',
            '.env': 'environment',
            'Makefile': 'make'
        }
        
        found_configs = {}
        for file in files:
            filename = Path(file).name
            if filename in config_patterns:
                content = self.fs.read_file(file)
                if content:
                    found_configs[filename] = content[:1000]  # First 1000 chars
        
        return found_configs
    
    def _build_scan_prompt(self, path: str, files: List[str], configs: Dict[str, str]) -> str:
        return f"""
Analyze this project structure and identify all technology stacks, frameworks, and dependencies.

Project Path: {path}

Key Files Found:
{json.dumps([f for f in files[:50]], indent=2)}

Configuration Files Content:
{json.dumps(configs, indent=2)}

Analyze and return a JSON object with:
{{
  "project_type": "web|api|cli|library|mobile|desktop|data|ml|devops|other",
  "technology_stacks": [
    {{
      "name": "technology name",
      "version": "detected or recommended version",
      "type": "language|framework|database|tool",
      "config_file": "path to config file",
      "confidence": 0.0-1.0
    }}
  ],
  "dependencies": {{
    "system": ["list of system packages needed"],
    "runtime": ["list of runtime dependencies"],
    "development": ["list of dev dependencies"]
  }},
  "entry_points": ["main files or scripts to run"],
  "build_commands": ["detected or inferred build commands"],
  "test_commands": ["detected or inferred test commands"],
  "special_requirements": ["any special setup requirements"],
  "complexity": "simple|moderate|complex"
}}
"""