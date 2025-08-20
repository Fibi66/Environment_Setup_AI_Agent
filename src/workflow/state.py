from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime


class State(TypedDict, total=False):
    # Input
    project_path: str
    preferences: Dict[str, Any]
    mode: str  # auto, interactive, dry-run
    
    # Scanning results
    scan_results: Dict[str, Any]
    detected_stacks: List[Dict[str, Any]]
    project_type: str
    dependencies: Dict[str, List[str]]
    
    # Analysis results
    dependency_graph: Dict[str, Any]
    compatibility_issues: List[Dict[str, Any]]
    optimization_suggestions: List[str]
    security_concerns: List[Dict[str, Any]]
    installation_order: List[Dict[str, Any]]
    
    # Planning results
    installation_plan: Dict[str, Any]
    estimated_time: str
    
    # Execution results
    execution_results: List[Dict[str, Any]]
    completed_steps: List[str]
    failed_steps: List[str]
    execution_log: List[Dict[str, Any]]
    success_rate: float
    
    # Verification results
    verification_results: List[Dict[str, Any]]
    verification_analysis: Dict[str, Any]
    installation_success: bool
    health_score: int
    
    # Reporting
    report: str
    report_path: str
    
    # Workflow control
    workflow_path: str
    start_time: datetime
    end_time: Optional[datetime]
    errors: List[Dict[str, Any]]
    user_cancelled: bool
    fatal_error: Optional[str]
    
    # Metadata
    orchestrator_version: str
    complexity: str
    estimated_duration: str
    requires_interaction: bool
    special_considerations: List[str]
    recommended_approach: str