from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import State
from ..agents import (
    OrchestratorAgent,
    ScannerAgent,
    AnalyzerAgent,
    PlannerAgent,
    ExecutorAgent,
    VerifierAgent,
    ReporterAgent
)


def create_workflow(config):
    # Initialize agents
    orchestrator = OrchestratorAgent(config)
    scanner = ScannerAgent(config)
    analyzer = AnalyzerAgent(config)
    planner = PlannerAgent(config)
    executor = ExecutorAgent(config)
    verifier = VerifierAgent(config)
    reporter = ReporterAgent(config)
    
    # Create workflow
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("orchestrate", orchestrator.process)
    workflow.add_node("scan", scanner.process)
    workflow.add_node("analyze", analyzer.process)
    workflow.add_node("plan", planner.process)
    workflow.add_node("execute", executor.process)
    workflow.add_node("verify", verifier.process)
    workflow.add_node("report", reporter.process)
    
    # Define edges
    workflow.set_entry_point("orchestrate")
    
    # Conditional routing based on workflow path
    def route_after_orchestrate(state: State) -> str:
        if state.get('workflow_path') == 'fast-track':
            return "scan"
        return "scan"
    
    def route_after_scan(state: State) -> str:
        if state.get('detected_stacks'):
            return "analyze"
        return "report"  # Nothing to install
    
    def route_after_analyze(state: State) -> str:
        if state.get('compatibility_issues'):
            # Critical issues might need user attention
            critical = any(
                issue['severity'] == 'critical' 
                for issue in state['compatibility_issues']
            )
            if critical:
                print("⚠️  Critical compatibility issues detected")
        return "plan"
    
    def route_after_plan(state: State) -> str:
        if state.get('installation_plan'):
            return "execute"
        return "report"  # No plan created
    
    def route_after_execute(state: State) -> str:
        if state.get('execution_results'):
            return "verify"
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
        {"plan": "plan"}
    )
    
    workflow.add_conditional_edges(
        "plan",
        route_after_plan,
        {"execute": "execute", "report": "report"}
    )
    
    workflow.add_conditional_edges(
        "execute",
        route_after_execute,
        {"verify": "verify", "report": "report"}
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