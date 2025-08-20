from typing import Dict, Any, List
from .base import BaseAgent
from ..core.safety import Action, ActionType


class PlannerAgent(BaseAgent):
    def __init__(self, config):
        super().__init__("Planner", "Installation Planning", config)
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("📋 Creating installation plan...")
        
        # Get analysis results
        analysis = {
            'scan_results': state.get('scan_results', {}),
            'dependency_graph': state.get('dependency_graph', {}),
            'installation_order': state.get('installation_order', []),
            'compatibility_issues': state.get('compatibility_issues', []),
            'system_info': self._get_system_info()
        }
        
        # Generate installation plan
        prompt = self._build_planning_prompt(analysis)
        plan = await self.think_json(prompt)
        
        # Mark critical steps for HITL
        plan = self._mark_critical_steps(plan)
        
        # Get user approval for the plan
        approved_plan = await self._get_plan_approval(plan, state)
        
        # Update state
        state['installation_plan'] = approved_plan
        state['estimated_time'] = plan.get('estimated_time', 'unknown')
        
        self.memory.remember('installation_plan', approved_plan, persistent=True)
        
        self.log(f"✅ Plan created with {len(approved_plan['steps'])} steps")
        
        return state
    
    def _get_system_info(self) -> Dict[str, Any]:
        import platform
        return {
            'os': platform.system(),
            'os_version': platform.version(),
            'architecture': platform.machine(),
            'python_version': platform.python_version()
        }
    
    def _build_planning_prompt(self, analysis: Dict) -> str:
        system_info = analysis.get('system_info', {})
        os_type = system_info.get('os', 'Unknown')
        
        # OS-specific instructions
        os_instructions = ""
        if os_type == "Windows":
            os_instructions = """
- Use Windows-appropriate commands ONLY
- For package installation use ONE of these in order of preference:
  1. winget install <package> --accept-package-agreements --accept-source-agreements
  2. choco install <package> -y (if Chocolatey is available)
  3. Direct download via PowerShell: Invoke-WebRequest -Uri <url> -OutFile <file>
- Do NOT use sudo, apt-get, yum, or other Linux commands
- Do NOT use bash commands like ./build.sh on Windows
- Use PowerShell or cmd commands only
- For build scripts: use build.bat or build.ps1, NOT build.sh
- Paths should use backslashes or be quoted
- requires_sudo should always be false on Windows
- Common Windows packages:
  - C++ Compiler: winget install Microsoft.VisualStudio.2022.BuildTools
  - CMake: winget install Kitware.CMake
  - Git: winget install Git.Git
  - Make: winget install GnuWin32.Make or use nmake from Visual Studio
"""
        elif os_type == "Darwin":  # macOS
            os_instructions = """
- Use macOS-appropriate commands (brew, port, or direct downloads)
- Use sudo only when necessary
- Consider using Homebrew for package management
"""
        else:  # Linux
            os_instructions = """
- Use Linux package managers (apt-get, yum, dnf, etc.)
- Use sudo for system-level changes
- Consider the specific Linux distribution
"""
        
        return f"""
Create a detailed installation plan based on the analysis.

System: {os_type}
Analysis Results:
{analysis}

Generate a JSON installation plan:
{{
  "steps": [
    {{
      "id": "step-id",
      "phase": "system|runtime|project|build|test",
      "name": "Step name",
      "description": "What this step does",
      "command": "exact command to run",
      "working_directory": "path or null",
      "requires_sudo": true/false,
      "can_parallel": true/false,
      "dependencies": ["list of step IDs this depends on"],
      "estimated_time_seconds": 30,
      "rollback_command": "command to undo this step or null",
      "success_indicators": ["expected output patterns"],
      "failure_indicators": ["error patterns to watch for"]
    }}
  ],
  "estimated_time": "2 minutes",
  "parallel_groups": [
    ["step-ids that can run in parallel"]
  ],
  "critical_steps": ["step-ids that are critical"],
  "notes": ["important notes for the user"]
}}

Important OS-Specific Requirements:
{os_instructions}

General Requirements:
- Order steps correctly based on dependencies
- Group parallel-safe operations
- Include rollback commands where possible
- Provide clear success/failure indicators
- Optimize for speed while maintaining safety
"""
    
    def _mark_critical_steps(self, plan: Dict) -> Dict:
        # Mark steps that need HITL approval
        for step in plan.get('steps', []):
            command = step.get('command', '')
            
            # Classify the action
            action_type = self.safety.classify_action(command)
            step['requires_confirmation'] = (action_type == ActionType.CRITICAL)
            
            # Add risk analysis
            if step['requires_confirmation']:
                step['risks'] = self.safety.analyze_risks(command)
        
        return plan
    
    async def _get_plan_approval(self, plan: Dict, state: Dict = None) -> Dict:
        print("\n" + "="*60)
        print("📋 INSTALLATION PLAN REVIEW")
        print("="*60)
        
        # Show summary
        steps = plan.get('steps', [])
        print(f"\nTotal steps: {len(steps)}")
        print(f"Estimated time: {plan.get('estimated_time', 'unknown')}")
        
        # Group by phase
        phases = {}
        for step in steps:
            phase = step.get('phase', 'unknown')
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(step)
        
        # Display by phase
        for phase, phase_steps in phases.items():
            print(f"\n{phase.upper()} Phase ({len(phase_steps)} steps):")
            for step in phase_steps:
                marker = "⚠️ " if step.get('requires_confirmation') else "  "
                print(f"{marker} • {step['name']}")
                if step.get('requires_sudo'):
                    print(f"      [sudo] {step['command'][:60]}...")
                else:
                    print(f"      {step['command'][:60]}...")
        
        # Show critical steps warning
        critical_count = sum(1 for s in steps if s.get('requires_confirmation'))
        if critical_count > 0:
            print(f"\n⚠️  {critical_count} steps require additional confirmation during execution")
        
        # Get approval
        print("\nOptions:")
        print("  [y] Approve and continue")
        print("  [n] Cancel installation")
        print("  [d] Show detailed plan")
        
        response = input("\nYour choice [y/n/d]: ").lower().strip()
        
        if response == 'd':
            # Show detailed plan
            import json
            print("\nDetailed Plan:")
            print(json.dumps(plan, indent=2))
            return await self._get_plan_approval(plan)
        elif response == 'y':
            return plan
        else:
            raise KeyboardInterrupt("Installation cancelled by user")