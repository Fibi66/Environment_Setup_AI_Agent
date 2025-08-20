from typing import Dict, Any, Optional
from datetime import datetime
from .base import BaseAgent


class OrchestratorAgent(BaseAgent):
    def __init__(self, config):
        super().__init__("Orchestrator", "Workflow Orchestration", config)
        self.config = config
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("🎯 Starting orchestration...")
        
        # Analyze initial request
        initial_analysis = await self._analyze_request(state)
        state.update(initial_analysis)
        
        # Determine workflow path
        workflow_path = await self._determine_workflow(state)
        state['workflow_path'] = workflow_path
        
        # Add metadata
        state['start_time'] = datetime.now()
        state['orchestrator_version'] = '1.0.0'
        
        self.log(f"✅ Workflow determined: {workflow_path}")
        
        return state
    
    async def _analyze_request(self, state: Dict) -> Dict:
        prompt = f"""
Analyze this setup request and determine the approach.

Request context:
- Project path: {state.get('project_path', 'not specified')}
- User preferences: {state.get('preferences', {})}
- Mode: {state.get('mode', 'auto')}

Return JSON:
{{
  "complexity": "simple|moderate|complex",
  "estimated_duration": "time estimate",
  "requires_interaction": true/false,
  "special_considerations": ["list of considerations"],
  "recommended_approach": "description"
}}
"""
        
        return await self.think_json(prompt)
    
    async def _determine_workflow(self, state: Dict) -> str:
        complexity = state.get('complexity', 'moderate')
        
        if complexity == 'simple':
            return 'fast-track'  # Skip detailed analysis
        elif complexity == 'complex':
            return 'comprehensive'  # Full analysis and verification
        else:
            return 'standard'  # Normal flow
    
    async def should_continue(self, state: Dict, current_agent: str) -> bool:
        # Determine if workflow should continue
        if state.get('fatal_error'):
            return False
        
        if state.get('user_cancelled'):
            return False
        
        # Check if critical steps failed
        if current_agent == 'executor':
            failed_critical = any(
                step_id in state.get('failed_steps', [])
                for step_id in state.get('installation_plan', {}).get('critical_steps', [])
            )
            if failed_critical:
                self.log("❌ Critical step failed, stopping workflow")
                return False
        
        return True
    
    async def handle_error(self, state: Dict, error: Exception, agent: str) -> Dict:
        self.log(f"⚠️  Error in {agent}: {error}")
        
        # Ask LLM for error handling strategy
        prompt = f"""
An error occurred during setup. Suggest how to handle it.

Error: {error}
Agent: {agent}
Current state summary: {self._summarize_state(state)}

Return JSON:
{{
  "can_continue": true/false,
  "recovery_action": "skip|retry|abort|manual",
  "user_message": "message to show user",
  "suggested_fix": "how to fix the issue"
}}
"""
        
        strategy = await self.think_json(prompt)
        
        # Update state with error info
        if 'errors' not in state:
            state['errors'] = []
        
        state['errors'].append({
            'agent': agent,
            'error': str(error),
            'strategy': strategy,
            'timestamp': datetime.now().isoformat()
        })
        
        # Show user message
        print(f"\n⚠️  {strategy['user_message']}")
        
        if strategy['recovery_action'] == 'manual':
            print(f"Suggested fix: {strategy['suggested_fix']}")
            input("Press Enter when ready to continue...")
        
        return state
    
    def _summarize_state(self, state: Dict) -> str:
        return {
            'project_type': state.get('project_type'),
            'detected_stacks': len(state.get('detected_stacks', [])),
            'completed_steps': len(state.get('completed_steps', [])),
            'failed_steps': len(state.get('failed_steps', []))
        }