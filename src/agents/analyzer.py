from typing import Dict, Any, List
from .base import BaseAgent


class AnalyzerAgent(BaseAgent):
    def __init__(self, config):
        super().__init__("Analyzer", "Dependency Analysis", config)
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("🔬 Analyzing dependencies and compatibility...")
        
        scan_results = state.get('scan_results', {})
        detected_stacks = state.get('detected_stacks', [])
        
        # Build analysis prompt
        prompt = self._build_analysis_prompt(scan_results, detected_stacks)
        
        # Get deep analysis from LLM
        analysis = await self.think_json(prompt)
        
        # Update state with analysis
        state['dependency_graph'] = analysis.get('dependency_graph', {})
        state['compatibility_issues'] = analysis.get('compatibility_issues', [])
        state['optimization_suggestions'] = analysis.get('optimizations', [])
        state['security_concerns'] = analysis.get('security_concerns', [])
        state['installation_order'] = analysis.get('installation_order', [])
        
        self.memory.remember('analysis_results', analysis)
        
        if state['compatibility_issues']:
            self.log(f"⚠️  Found {len(state['compatibility_issues'])} compatibility issues")
        else:
            self.log("✅ No compatibility issues detected")
        
        return state
    
    def _build_analysis_prompt(self, scan_results: Dict, stacks: List) -> str:
        return f"""
Perform deep analysis of the project dependencies and compatibility.

Scan Results:
{scan_results}

Technology Stacks:
{stacks}

Analyze and return a JSON object with:
{{
  "dependency_graph": {{
    "nodes": [
      {{
        "id": "package-name",
        "type": "system|runtime|dev",
        "version": "version-string",
        "required_by": ["list of dependents"]
      }}
    ],
    "edges": [
      {{"from": "package-a", "to": "package-b", "type": "depends|conflicts"}}
    ]
  }},
  "compatibility_issues": [
    {{
      "severity": "critical|warning|info",
      "packages": ["affected packages"],
      "issue": "description of the issue",
      "solution": "recommended solution"
    }}
  ],
  "installation_order": [
    {{
      "phase": "system|runtime|project",
      "packages": ["ordered list of packages"],
      "parallel_safe": true/false
    }}
  ],
  "optimizations": [
    {{
      "type": "performance|size|security",
      "suggestion": "optimization suggestion",
      "impact": "expected impact"
    }}
  ],
  "security_concerns": [
    {{
      "severity": "critical|high|medium|low",
      "component": "affected component",
      "issue": "security issue description",
      "mitigation": "how to mitigate"
    }}
  ]
}}

Consider:
- Version conflicts between packages
- System vs runtime dependencies
- Installation order requirements
- Parallel installation opportunities
- Known vulnerabilities
- Best practices for each technology
"""