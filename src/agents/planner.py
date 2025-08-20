from typing import Dict, Any, List, Optional
from .base import BaseAgent
from .executors import NodeExecutor, PythonExecutor, JavaExecutor


class PlannerAgent(BaseAgent):
    def __init__(self, config):
        super().__init__("Planner", "Language Environment Router", config)
        self.config = config
        
        # Initialize all executors
        self.executors = {
            'nodejs': NodeExecutor(config),
            'python': PythonExecutor(config),
            'java': JavaExecutor(config)
        }
        
        # Define execution order priority
        self.language_priority = {
            'java': 1,     # Java first (JDK needed by some tools)
            'python': 2,   # Python second
            'nodejs': 3    # Node.js last
        }
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("📋 Planning language environment setup...")
        
        detected_languages = state.get('detected_languages', [])
        
        if not detected_languages:
            self.log("⚠️ No languages to set up")
            state['workflow_should_end'] = True
            return state
        
        # Sort languages by priority
        sorted_languages = sorted(
            detected_languages,
            key=lambda x: self.language_priority.get(x, 999)
        )
        
        self.log(f"Setup order: {' → '.join(sorted_languages)}")
        
        # Initialize execution tracking if not present
        if 'execution_queue' not in state:
            state['execution_queue'] = sorted_languages
        if 'completed_languages' not in state:
            state['completed_languages'] = []
        if 'failed_languages' not in state:
            state['failed_languages'] = []
        
        # Store the sorted order
        state['execution_queue'] = sorted_languages
        state['current_language_index'] = 0
        
        self.log(f"✅ Plan created for {len(sorted_languages)} language(s)")
        
        return state
    
    async def execute_next_language(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the next language in the queue"""
        
        execution_queue = state.get('execution_queue', [])
        completed = state.get('completed_languages', [])
        failed = state.get('failed_languages', [])
        current_index = state.get('current_language_index', 0)
        
        # Find next language to execute
        remaining = [lang for lang in execution_queue if lang not in completed and lang not in failed]
        
        if not remaining:
            self.log("✅ All language environments processed")
            state['all_languages_processed'] = True
            return state
        
        current_language = remaining[0]
        self.log(f"\n🔄 Processing: {current_language}")
        
        # Get the appropriate executor
        executor = self.executors.get(current_language)
        
        if not executor:
            self.log(f"❌ No executor found for {current_language}")
            state['failed_languages'].append(current_language)
            return state
        
        # Execute the language setup
        try:
            state = await executor.process(state)
            
            # Check if language failed
            if current_language in state.get('failed_languages', []):
                self.log(f"❌ {current_language} setup failed")
                
                # Decide whether to continue with other languages
                if self._should_continue_after_failure(current_language, state):
                    self.log("↳ Continuing with remaining languages...")
                else:
                    self.log("↳ Stopping due to critical failure")
                    state['workflow_should_end'] = True
                    return state
            
        except Exception as e:
            self.log(f"❌ Error executing {current_language}: {str(e)}")
            state['failed_languages'].append(current_language)
            
            if not self._should_continue_after_failure(current_language, state):
                state['workflow_should_end'] = True
                return state
        
        # Update progress
        state['current_language_index'] = current_index + 1
        
        # Check if more languages to process
        remaining_after = [lang for lang in execution_queue 
                          if lang not in state.get('completed_languages', []) 
                          and lang not in state.get('failed_languages', [])]
        
        if remaining_after:
            self.log(f"📋 Remaining: {', '.join(remaining_after)}")
            state['has_more_languages'] = True
        else:
            self.log("✅ All languages processed")
            state['all_languages_processed'] = True
            state['has_more_languages'] = False
        
        return state
    
    def _should_continue_after_failure(self, failed_language: str, state: Dict[str, Any]) -> bool:
        """Determine if we should continue after a language fails"""
        
        # If Java fails, it might affect other languages that need JVM
        if failed_language == 'java':
            remaining = state.get('execution_queue', [])
            # Check if any remaining languages might need Java
            if 'scala' in remaining or 'kotlin' in remaining:
                return False
        
        # Generally continue with other languages
        return True
    
    def get_summary(self, state: Dict[str, Any]) -> str:
        """Get a summary of the execution results"""
        completed = state.get('completed_languages', [])
        failed = state.get('failed_languages', [])
        
        summary_parts = []
        
        if completed:
            summary_parts.append(f"✅ Completed: {', '.join(completed)}")
        
        if failed:
            summary_parts.append(f"❌ Failed: {', '.join(failed)}")
        
        if not completed and not failed:
            summary_parts.append("No languages were processed")
        
        return " | ".join(summary_parts)