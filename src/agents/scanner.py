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
        
        # Detect languages
        detected_languages = self._detect_languages(files, config_files)
        
        # Check for unsupported languages
        supported_languages = {'nodejs', 'python', 'java'}
        unsupported = detected_languages - supported_languages
        
        if unsupported:
            self.log(f"❌ Unsupported languages detected: {', '.join(unsupported)}")
            state['error'] = f"Sorry, we currently only support Node.js, Python, and Java. Detected {', '.join(unsupported)} is not yet supported."
            state['workflow_should_end'] = True
            state['detected_languages'] = []
            
            # Record error in tracker
            if 'error_tracker' in state:
                from ..core.errors import SetupError, ErrorType, ErrorSeverity
                error = SetupError(
                    error_type=ErrorType.UNSUPPORTED_LANGUAGE,
                    message=state['error'],
                    severity=ErrorSeverity.CRITICAL,
                    agent="ScannerAgent",
                    details={'unsupported_languages': list(unsupported)}
                )
                state['error_tracker'].add_error(error)
            
            return state
        
        # Filter to only supported languages
        detected_languages = detected_languages & supported_languages
        
        if not detected_languages:
            self.log("⚠️ No supported languages detected")
            state['detected_languages'] = []
            state['workflow_should_end'] = True
            return state
        
        # Get detailed config for each language
        language_configs = await self._analyze_language_configs(detected_languages, config_files, files)
        
        # Update state
        state['detected_languages'] = list(detected_languages)
        state['language_configs'] = language_configs
        state['execution_queue'] = list(detected_languages)  # Will be ordered by planner
        state['completed_languages'] = []
        state['failed_languages'] = []
        
        self.log(f"✅ Detected supported languages: {', '.join(detected_languages)}")
        
        return state
    
    def _find_config_files(self, files: List[str]) -> Dict[str, str]:
        # Common config file extensions and patterns that likely contain project configuration
        config_indicators = [
            '.json', '.yaml', '.yml', '.toml', '.xml', '.gradle', '.sbt',
            '.csproj', '.fsproj', '.vbproj', '.proj', '.props', '.targets',
            '.lock', '.mod', '.sum', 'file', 'file.lock', '.config.js',
            '.config.ts', '.conf', '.ini', '.cfg', '.properties'
        ]
        
        # Important files regardless of extension
        important_files = [
            'Makefile', 'makefile', 'GNUmakefile', 'Dockerfile', 
            'docker-compose', 'Jenkinsfile', 'Procfile', '.env',
            'setup.py', 'setup.cfg', 'build.sh', 'build.bat', 'build.ps1'
        ]
        
        found_configs = {}
        for file in files:
            filename = Path(file).name.lower()
            
            # Check if it's a config file or important file
            is_config = any(filename.endswith(ext) for ext in config_indicators)
            is_important = any(filename == imp.lower() for imp in important_files)
            
            if is_config or is_important:
                content = self.fs.read_file(file)
                if content:
                    # Use original filename (not lowercased) as key
                    original_filename = Path(file).name
                    found_configs[original_filename] = content[:2000]  # First 2000 chars for better context
        
        return found_configs
    
    def _detect_languages(self, files: List[str], config_files: Dict[str, str]) -> set:
        """Detect programming languages in the project"""
        languages = set()
        
        # Node.js detection
        if 'package.json' in config_files:
            languages.add('nodejs')
        
        # Python detection
        if any(f in config_files for f in ['requirements.txt', 'Pipfile', 'pyproject.toml', 'setup.py']):
            languages.add('python')
        
        # Java detection
        if any(f in config_files for f in ['pom.xml', 'build.gradle', 'build.gradle.kts']):
            languages.add('java')
        
        # Check file extensions for additional detection
        for file in files:
            if file.endswith('.js') or file.endswith('.ts') or file.endswith('.jsx') or file.endswith('.tsx'):
                languages.add('nodejs')
            elif file.endswith('.py'):
                languages.add('python')
            elif file.endswith('.java'):
                languages.add('java')
            # Detect unsupported languages
            elif file.endswith('.rb'):
                languages.add('ruby')
            elif file.endswith('.go'):
                languages.add('golang')
            elif file.endswith('.rs'):
                languages.add('rust')
            elif file.endswith('.php'):
                languages.add('php')
            elif file.endswith('.cs'):
                languages.add('csharp')
            elif file.endswith('.swift'):
                languages.add('swift')
        
        return languages
    
    async def _analyze_language_configs(self, languages: set, config_files: Dict[str, str], files: List[str]) -> Dict:
        """Get detailed configuration for each detected language"""
        configs = {}
        
        if 'nodejs' in languages:
            configs['nodejs'] = {
                'has_package_json': 'package.json' in config_files,
                'has_package_lock': 'package-lock.json' in config_files,
                'has_yarn_lock': 'yarn.lock' in config_files,
                'package_manager': 'yarn' if 'yarn.lock' in config_files else 'npm'
            }
        
        if 'python' in languages:
            configs['python'] = {
                'has_requirements': 'requirements.txt' in config_files,
                'has_pipfile': 'Pipfile' in config_files,
                'has_pyproject': 'pyproject.toml' in config_files,
                'has_setup_py': 'setup.py' in config_files,
                'use_venv': True  # Always use virtual environment
            }
        
        if 'java' in languages:
            configs['java'] = {
                'has_pom': 'pom.xml' in config_files,
                'has_gradle': any(f in config_files for f in ['build.gradle', 'build.gradle.kts']),
                'build_tool': 'maven' if 'pom.xml' in config_files else 'gradle'
            }
        
        return configs
    
    def _build_scan_prompt(self, path: str, files: List[str], configs: Dict[str, str]) -> str:
        return f"""
Analyze this project structure and identify all technology stacks, frameworks, and dependencies.

Project Path: {path}

All Files Found (first 100):
{json.dumps([f for f in files[:100]], indent=2)}

Potential Configuration Files Content:
{json.dumps(configs, indent=2)}

Based on the file list and configuration contents, identify ALL technology stacks, languages, frameworks, and tools used in this project.

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