import re
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    SAFE = "safe"
    REVIEW = "review"
    CRITICAL = "critical"


@dataclass
class Action:
    command: str
    description: str
    type: ActionType
    risks: List[str] = None
    
    def __post_init__(self):
        if self.risks is None:
            self.risks = []


@dataclass
class SafetyDecision:
    approved: bool
    auto: bool
    modified_command: Optional[str] = None
    reason: Optional[str] = None


class SafetyController:
    def __init__(self, config):
        self.config = config.get_safety_config()
        self.critical_patterns = [re.compile(p) for p in self.config.critical_patterns]
        self.auto_approve_patterns = [re.compile(p) for p in self.config.auto_approve]
    
    def classify_action(self, command: str) -> ActionType:
        # Check if it's a critical command
        for pattern in self.critical_patterns:
            if pattern.search(command):
                return ActionType.CRITICAL
        
        # Check if it's auto-approvable
        for pattern in self.auto_approve_patterns:
            if pattern.search(command):
                return ActionType.SAFE
        
        # Default to review
        return ActionType.REVIEW
    
    def analyze_risks(self, command: str) -> List[str]:
        risks = []
        
        if 'sudo' in command:
            risks.append("Requires system-level permissions")
        
        if 'rm' in command and '-r' in command:
            risks.append("Deletes files/directories recursively")
        
        if '|' in command and 'sh' in command:
            risks.append("Executes downloaded content directly")
        
        if 'chmod 777' in command:
            risks.append("Makes files world-writable (security risk)")
        
        if 'curl' in command or 'wget' in command:
            risks.append("Downloads content from internet")
        
        return risks
    
    async def check_action(self, action: Action) -> SafetyDecision:
        if not self.config.enabled:
            return SafetyDecision(approved=True, auto=True)
        
        # Auto-approve safe actions
        if action.type == ActionType.SAFE:
            return SafetyDecision(approved=True, auto=True, reason="Auto-approved safe command")
        
        # Critical actions always need confirmation
        if action.type == ActionType.CRITICAL:
            return await self.request_human_approval(action)
        
        # Review actions might be auto-approved based on context
        if action.type == ActionType.REVIEW:
            if self._can_auto_approve(action):
                return SafetyDecision(approved=True, auto=True, reason="Auto-approved after review")
            return await self.request_human_approval(action)
        
        return SafetyDecision(approved=False, auto=True, reason="Unknown action type")
    
    def _can_auto_approve(self, action: Action) -> bool:
        # Simple heuristics for auto-approval
        safe_keywords = ['mkdir', 'cd', 'echo', 'export', 'source']
        command_start = action.command.split()[0] if action.command else ""
        return command_start in safe_keywords
    
    async def request_human_approval(self, action: Action) -> SafetyDecision:
        print("\n" + "="*60)
        print("🔒 APPROVAL REQUIRED")
        print("="*60)
        print(f"Command: {action.command}")
        print(f"Purpose: {action.description}")
        
        if action.risks:
            print("\n⚠️  Potential Risks:")
            for risk in action.risks:
                print(f"  • {risk}")
        
        print("\nOptions:")
        print("  [y] Approve and continue")
        print("  [n] Skip this step")
        print("  [e] Edit command")
        print("  [q] Quit")
        
        # Simulate timeout with asyncio
        try:
            response = await asyncio.wait_for(
                self._get_user_input("Your choice [y/n/e/q]: "),
                timeout=self.config.auto_approve_timeout
            )
        except asyncio.TimeoutError:
            print("\n⏱️ Timeout - automatically rejecting for safety")
            return SafetyDecision(approved=False, auto=False, reason="Timeout")
        
        response = response.lower().strip()
        
        if response == 'y':
            return SafetyDecision(approved=True, auto=False)
        elif response == 'n':
            return SafetyDecision(approved=False, auto=False, reason="User skipped")
        elif response == 'e':
            new_command = await self._get_user_input("Enter modified command: ")
            return SafetyDecision(approved=True, auto=False, modified_command=new_command)
        elif response == 'q':
            raise KeyboardInterrupt("User quit")
        else:
            return SafetyDecision(approved=False, auto=False, reason="Invalid response")
    
    async def _get_user_input(self, prompt: str) -> str:
        # In real implementation, this would be properly async
        return input(prompt)