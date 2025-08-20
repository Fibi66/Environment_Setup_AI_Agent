import asyncio
import subprocess
from typing import Dict, Any, List, Optional
from .base import BaseAgent
from ..core.safety import Action, ActionType


class ExecutorAgent(BaseAgent):
    def __init__(self, config):
        super().__init__("Executor", "Command Execution", config)
        self.execution_log = []
        self.completed_steps = []
        self.failed_steps = []
    
    def _check_admin(self) -> bool:
        """Check if running with admin privileges on Windows"""
        import platform
        if platform.system() != "Windows":
            return True
        
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("🚀 Starting execution...")
        
        # Check if Windows and needs admin rights
        import platform
        if platform.system() == "Windows":
            if not self._check_admin():
                self.log("⚠️  Windows detected - Administrator privileges required")
                print("\n" + "="*60)
                print("🔐 ADMINISTRATOR PRIVILEGES REQUIRED")
                print("="*60)
                print("\nPlease restart this program as Administrator:")
                print("1. Right-click on your terminal/PowerShell/CMD")
                print("2. Select 'Run as Administrator'")
                print("3. Run the command again")
                print("\nThis allows installation of required software without timeouts.")
                print("="*60)
                raise SystemExit("Please run as Administrator")
        
        plan = state.get('installation_plan', {})
        steps = plan.get('steps', [])
        
        # Execute steps
        results = []
        for i, step in enumerate(steps):
            self.log(f"[{i+1}/{len(steps)}] {step['name']}")
            
            # Check if step needs confirmation
            if step.get('requires_confirmation'):
                action = Action(
                    command=step['command'],
                    description=step['description'],
                    type=ActionType.CRITICAL,
                    risks=step.get('risks', [])
                )
                
                decision = await self.safety.check_action(action)
                
                if not decision.approved:
                    self.log(f"⏭️  Skipped: {step['name']}")
                    results.append({
                        'step_id': step['id'],
                        'status': 'skipped',
                        'reason': decision.reason
                    })
                    continue
                
                if decision.modified_command:
                    step['command'] = decision.modified_command
            
            # Execute the step
            result = await self._execute_step(step)
            results.append(result)
            
            if result['status'] == 'success':
                self.completed_steps.append(step['id'])
                self.log(f"✅ {step['name']}")
            else:
                self.failed_steps.append(step['id'])
                self.log(f"❌ {step['name']}: {result.get('error', 'Unknown error')}")
                
                # Try to recover
                recovery = await self._attempt_recovery(step, result)
                if recovery:
                    results.append(recovery)
                    if recovery['status'] == 'success':
                        self.completed_steps.append(step['id'])
                        self.failed_steps.remove(step['id'])
        
        # Update state
        state['execution_results'] = results
        state['completed_steps'] = self.completed_steps
        state['failed_steps'] = self.failed_steps
        state['execution_log'] = self.execution_log
        
        success_rate = len(self.completed_steps) / len(steps) if steps else 0
        state['success_rate'] = success_rate
        
        self.log(f"✅ Execution complete: {len(self.completed_steps)}/{len(steps)} succeeded")
        
        return state
    
    async def _execute_step(self, step: Dict) -> Dict:
        result = {
            'step_id': step['id'],
            'name': step['name'],
            'command': step['command']
        }
        
        try:
            # Prepare command
            command = step['command']
            
            # On Windows, don't use sudo
            import platform
            if platform.system() != "Windows" and step.get('requires_sudo'):
                command = f"sudo {command}"
            
            # Set working directory
            cwd = step.get('working_directory', '.')
            
            # Debug: Show command being executed
            self.log(f"  Executing: {command[:100]}...")
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            try:
                # Get output
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=step.get('estimated_time_seconds', 300)
                )
            finally:
                # Ensure process is terminated on Windows
                if process.returncode is None:
                    try:
                        process.terminate()
                        await asyncio.wait_for(process.wait(), timeout=2)
                    except:
                        process.kill()
                        await process.wait()
            
            # Log execution
            self.execution_log.append({
                'step': step['name'],
                'command': command,
                'stdout': stdout.decode() if stdout else '',
                'stderr': stderr.decode() if stderr else '',
                'return_code': process.returncode
            })
            
            # Check success
            if process.returncode == 0:
                result['status'] = 'success'
                result['output'] = stdout.decode() if stdout else ''
            else:
                result['status'] = 'failed'
                result['error'] = stderr.decode() if stderr else 'Command failed'
                result['return_code'] = process.returncode
            
        except asyncio.TimeoutError:
            result['status'] = 'failed'
            result['error'] = f"Timeout after {step.get('estimated_time_seconds', 300)} seconds"
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
        
        return result
    
    async def _attempt_recovery(self, step: Dict, result: Dict) -> Optional[Dict]:
        self.log(f"🔧 Attempting recovery for: {step['name']}")
        
        # Ask LLM for recovery strategy
        prompt = f"""
A step failed during installation. Suggest a recovery strategy.

Failed Step:
- Name: {step['name']}
- Command: {step['command']}
- Error: {result.get('error', 'Unknown')}

Provide a JSON response:
{{
  "can_recover": true/false,
  "recovery_command": "command to fix the issue",
  "explanation": "why this might work",
  "skip_safe": true/false
}}
"""
        
        recovery_plan = await self.think_json(prompt)
        
        if not recovery_plan.get('can_recover'):
            if recovery_plan.get('skip_safe'):
                self.log("⚠️  Step can be safely skipped")
                return None
            else:
                self.log("❌ No recovery possible")
                return None
        
        # Try recovery command
        self.log(f"Trying: {recovery_plan['recovery_command']}")
        
        recovery_step = {
            'id': f"{step['id']}_recovery",
            'name': f"Recovery: {step['name']}",
            'command': recovery_plan['recovery_command'],
            'description': recovery_plan['explanation'],
            'requires_sudo': step.get('requires_sudo', False),
            'working_directory': step.get('working_directory', '.'),
            'estimated_time_seconds': 60
        }
        
        return await self._execute_step(recovery_step)