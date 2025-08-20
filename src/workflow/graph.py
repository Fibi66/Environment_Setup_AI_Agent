from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import State
from ..agents import (
    OrchestratorAgent,
    ScannerAgent,
    AnalyzerAgent,
    PlannerAgent,
    VerifierAgent,
    ReporterAgent
)


def create_workflow(config):
    # Initialize agents
    orchestrator = OrchestratorAgent(config)
    scanner = ScannerAgent(config)
    analyzer = AnalyzerAgent(config)
    planner = PlannerAgent(config)
    verifier = VerifierAgent(config)
    reporter = ReporterAgent(config)
    
    # Create workflow
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("orchestrate", orchestrator.process)
    workflow.add_node("scan", scanner.process)
    workflow.add_node("analyze", analyzer.process)
    workflow.add_node("plan", planner.process)
    workflow.add_node("execute_language", planner.execute_next_language)  # Router + Executor
    workflow.add_node("verify", verifier.process)
    workflow.add_node("report", reporter.process)
    
    # Define edges
    workflow.set_entry_point("orchestrate")
    
    # Conditional routing based on workflow state
    def route_after_orchestrate(state: State) -> str:
        return "scan"
    
    def route_after_scan(state: State) -> str:
        # Check if workflow should end (unsupported languages)
        if state.get('workflow_should_end'):
            return "report"
        
        # Check if languages were detected
        if state.get('detected_languages'):
            return "analyze"
        
        return "report"  # No languages to install
    
    def route_after_analyze(state: State) -> str:
        # Always go to planner if we have languages
        if state.get('detected_languages'):
            return "plan"
        return "report"
    
    def route_after_plan(state: State) -> str:
        # Check if we have languages to execute
        if state.get('execution_queue'):
            return "execute_language"
        return "report"  # No plan created
    
    def route_after_execute(state: State) -> str:
        # Check if all languages are processed
        if state.get('all_languages_processed'):
            # Go to verifier if at least one language succeeded
            if state.get('completed_languages'):
                return "verify"
            else:
                return "report"  # All failed, skip verification
        
        # Check if workflow should end (critical failure)
        if state.get('workflow_should_end'):
            return "report"
        
        # More languages to process - loop back
        if state.get('has_more_languages'):
            return "execute_language"
        
        # Default to report
        return "report"
    
    def route_after_verify(state: State) -> str:
        return "report"
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "orchestrate",
        route_after_orchestrate,
        {"scan": "scan"}
    )
    
    workflow.add_conditional_edges(
        "scan",
        route_after_scan,
        {"analyze": "analyze", "report": "report"}
    )
    
    workflow.add_conditional_edges(
        "analyze",
        route_after_analyze,
        {"plan": "plan", "report": "report"}
    )
    
    workflow.add_conditional_edges(
        "plan",
        route_after_plan,
        {"execute_language": "execute_language", "report": "report"}
    )
    
    # This is the key loop - execute_language can route back to itself
    workflow.add_conditional_edges(
        "execute_language",
        route_after_execute,
        {
            "execute_language": "execute_language",  # Loop back for next language
            "verify": "verify",
            "report": "report"
        }
    )
    
    workflow.add_conditional_edges(
        "verify",
        route_after_verify,
        {"report": "report"}
    )
    
    # Report always ends
    workflow.add_edge("report", END)
    
    # Compile with memory
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app