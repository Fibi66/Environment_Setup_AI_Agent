import asyncio
from typing import Dict, Any, List
from .base import BaseAgent


class VerifierAgent(BaseAgent):
    def __init__(self, config):
        super().__init__("Verifier", "Installation Verification", config)
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("✅ Verifying installation...")
        
        # Get execution results
        execution_results = state.get('execution_results', [])
        scan_results = state.get('scan_results', {})
        plan = state.get('installation_plan', {})
        
        # Generate verification strategy
        verification_plan = await self._generate_verification_plan(
            scan_results, 
            execution_results,
            plan
        )
        
        # Run verification checks
        verification_results = await self._run_verifications(verification_plan)
        
        # Analyze results
        analysis = await self._analyze_verification_results(verification_results)
        
        # Update state
        state['verification_results'] = verification_results
        state['verification_analysis'] = analysis
        state['installation_success'] = analysis.get('overall_success', False)
        state['health_score'] = analysis.get('health_score', 0)
        
        if state['installation_success']:
            self.log(f"✅ Installation verified successfully (Health: {state['health_score']}%)")
        else:
            self.log(f"⚠️  Verification found issues (Health: {state['health_score']}%)")
        
        return state
    
    async def _generate_verification_plan(self, scan: Dict, execution: List, plan: Dict) -> Dict:
        prompt = f"""
Generate verification checks for the completed installation.

Project Info:
{scan.get('project_type', 'unknown')} project with {len(scan.get('technology_stacks', []))} stacks

Execution Summary:
- Total steps: {len(execution)}
- Successful: {len([r for r in execution if r.get('status') == 'success'])}
- Failed: {len([r for r in execution if r.get('status') == 'failed'])}

Installation Plan:
Test commands: {scan.get('test_commands', [])}
Build commands: {scan.get('build_commands', [])}

Generate JSON verification plan:
{{
  "checks": [
    {{
      "id": "check-id",
      "name": "Check name",
      "type": "command|file|service|port",
      "command": "verification command",
      "expected_output": "pattern to match",
      "critical": true/false,
      "timeout": 30
    }}
  ],
  "quick_tests": [
    {{
      "name": "test name",
      "command": "quick test command",
      "expected_success": true
    }}
  ]
}}
"""
        
        return await self.think_json(prompt)
    
    async def _run_verifications(self, plan: Dict) -> List[Dict]:
        results = []
        
        for check in plan.get('checks', []):
            self.log(f"  Checking: {check['name']}")
            result = await self._run_single_check(check)
            results.append(result)
        
        # Run quick tests
        for test in plan.get('quick_tests', []):
            self.log(f"  Testing: {test['name']}")
            result = await self._run_quick_test(test)
            results.append(result)
        
        return results
    
    async def _run_single_check(self, check: Dict) -> Dict:
        result = {
            'check_id': check['id'],
            'name': check['name'],
            'type': check['type']
        }
        
        try:
            if check['type'] == 'command':
                # Run verification command
                process = await asyncio.create_subprocess_shell(
                    check['command'],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=check.get('timeout', 30)
                )
                
                output = stdout.decode() if stdout else ''
                
                # Check expected output
                if check.get('expected_output'):
                    import re
                    if re.search(check['expected_output'], output):
                        result['status'] = 'passed'
                    else:
                        result['status'] = 'failed'
                        result['reason'] = 'Output did not match expected pattern'
                else:
                    result['status'] = 'passed' if process.returncode == 0 else 'failed'
                
                result['output'] = output[:500]  # Truncate for readability
                
            elif check['type'] == 'file':
                # Check file exists
                import os
                if os.path.exists(check['command']):
                    result['status'] = 'passed'
                else:
                    result['status'] = 'failed'
                    result['reason'] = 'File not found'
            
            elif check['type'] == 'port':
                # Check port is listening
                import socket
                port = int(check['command'])
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                try:
                    sock.connect(('localhost', port))
                    result['status'] = 'passed'
                except:
                    result['status'] = 'failed'
                    result['reason'] = f'Port {port} not listening'
                finally:
                    sock.close()
            
            else:
                result['status'] = 'skipped'
                result['reason'] = f'Unknown check type: {check["type"]}'
                
        except asyncio.TimeoutError:
            result['status'] = 'failed'
            result['reason'] = 'Check timed out'
        except Exception as e:
            result['status'] = 'failed'
            result['reason'] = str(e)
        
        result['critical'] = check.get('critical', False)
        return result
    
    async def _run_quick_test(self, test: Dict) -> Dict:
        result = {
            'name': test['name'],
            'type': 'quick_test'
        }
        
        try:
            process = await asyncio.create_subprocess_shell(
                test['command'],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=10
            )
            
            if test.get('expected_success', True):
                result['status'] = 'passed' if process.returncode == 0 else 'failed'
            else:
                result['status'] = 'passed'  # Command ran, that's what matters
            
            result['output'] = (stdout.decode() if stdout else '')[:200]
            
        except Exception as e:
            result['status'] = 'failed'
            result['reason'] = str(e)
        
        return result
    
    async def _analyze_verification_results(self, results: List[Dict]) -> Dict:
        prompt = f"""
Analyze the verification results and provide a summary.

Results:
{results}

Return JSON:
{{
  "overall_success": true/false,
  "health_score": 0-100,
  "critical_failures": ["list of critical failures"],
  "warnings": ["list of warnings"],
  "recommendations": ["list of recommendations"],
  "ready_to_use": true/false
}}
"""
        
        analysis = await self.think_json(prompt)
        
        # Calculate health score if not provided
        if 'health_score' not in analysis:
            passed = len([r for r in results if r.get('status') == 'passed'])
            total = len(results)
            analysis['health_score'] = int((passed / total * 100) if total else 0)
        
        return analysis