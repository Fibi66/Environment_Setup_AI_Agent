"""Metrics tracking and export for the setup agent."""

import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path


class LanguageMetrics:
    """Track metrics for a specific language setup"""
    
    def __init__(self, language: str):
        self.language = language
        self.start_time = None
        self.end_time = None
        self.status = "pending"  # pending, in_progress, success, failed
        self.steps_completed = 0
        self.steps_total = 0
        self.errors = []
        self.commands_executed = []
        
    def start(self):
        """Mark the start of language setup"""
        self.start_time = time.time()
        self.status = "in_progress"
    
    def complete(self, success: bool = True):
        """Mark the completion of language setup"""
        self.end_time = time.time()
        self.status = "success" if success else "failed"
    
    def add_command(self, command: str, success: bool, duration: float):
        """Record a command execution"""
        self.commands_executed.append({
            'command': command[:100],  # Truncate long commands
            'success': success,
            'duration': duration
        })
        if success:
            self.steps_completed += 1
    
    def add_error(self, error: str):
        """Record an error"""
        self.errors.append(error)
    
    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.steps_total == 0:
            return 0.0
        return (self.steps_completed / self.steps_total) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export"""
        return {
            'language': self.language,
            'status': self.status,
            'duration_seconds': self.duration,
            'success_rate': self.success_rate,
            'steps_completed': self.steps_completed,
            'steps_total': self.steps_total,
            'errors_count': len(self.errors),
            'commands_count': len(self.commands_executed)
        }


class SetupMetrics:
    """Overall metrics tracking for the entire setup process"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.language_metrics: Dict[str, LanguageMetrics] = {}
        self.total_errors = 0
        self.project_info = {}
        
    def start(self, project_path: str = None):
        """Start metrics tracking"""
        self.start_time = time.time()
        self.project_info = {
            'project_path': project_path,
            'start_timestamp': datetime.now().isoformat(),
            'platform': self._get_platform()
        }
    
    def complete(self):
        """Mark setup as complete"""
        self.end_time = time.time()
    
    def add_language(self, language: str) -> LanguageMetrics:
        """Add a language to track"""
        if language not in self.language_metrics:
            self.language_metrics[language] = LanguageMetrics(language)
        return self.language_metrics[language]
    
    def get_language_metrics(self, language: str) -> Optional[LanguageMetrics]:
        """Get metrics for a specific language"""
        return self.language_metrics.get(language)
    
    @property
    def duration(self) -> Optional[float]:
        """Get total duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return None
    
    @property
    def overall_success_rate(self) -> float:
        """Calculate overall success rate"""
        successful = sum(1 for m in self.language_metrics.values() if m.status == "success")
        total = len(self.language_metrics)
        if total == 0:
            return 0.0
        return (successful / total) * 100
    
    @property
    def languages_succeeded(self) -> List[str]:
        """Get list of successfully setup languages"""
        return [lang for lang, m in self.language_metrics.items() if m.status == "success"]
    
    @property
    def languages_failed(self) -> List[str]:
        """Get list of failed languages"""
        return [lang for lang, m in self.language_metrics.items() if m.status == "failed"]
    
    def _get_platform(self) -> str:
        """Get platform information"""
        import platform
        return f"{platform.system()} {platform.release()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all metrics to dictionary for export"""
        return {
            'summary': {
                'total_duration_seconds': self.duration,
                'overall_success_rate': self.overall_success_rate,
                'languages_attempted': len(self.language_metrics),
                'languages_succeeded': len(self.languages_succeeded),
                'languages_failed': len(self.languages_failed),
                'total_errors': self.total_errors
            },
            'project_info': self.project_info,
            'languages': {
                lang: metrics.to_dict() 
                for lang, metrics in self.language_metrics.items()
            },
            'succeeded_languages': self.languages_succeeded,
            'failed_languages': self.languages_failed,
            'timestamp': datetime.now().isoformat()
        }
    
    def export_json(self, filepath: str = None) -> str:
        """Export metrics to JSON file"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"metrics/setup_metrics_{timestamp}.json"
        
        # Create directory if needed
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        # Write metrics
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        return filepath
    
    def export_summary(self) -> str:
        """Generate a human-readable summary"""
        lines = [
            "=" * 50,
            "SETUP METRICS SUMMARY",
            "=" * 50,
            f"Duration: {self.duration:.1f}s" if self.duration else "Duration: In progress",
            f"Success Rate: {self.overall_success_rate:.1f}%",
            f"Languages: {', '.join(self.language_metrics.keys())}",
            ""
        ]
        
        # Per-language summary
        for lang, metrics in self.language_metrics.items():
            status_emoji = "✅" if metrics.status == "success" else "❌" if metrics.status == "failed" else "⏳"
            lines.append(
                f"{status_emoji} {lang}: {metrics.status} "
                f"({metrics.duration:.1f}s)" if metrics.duration else f"({lang}: {metrics.status})"
            )
        
        lines.append("=" * 50)
        return "\n".join(lines)


# Global metrics instance (singleton pattern)
_metrics_instance = None

def get_metrics() -> SetupMetrics:
    """Get the global metrics instance"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = SetupMetrics()
    return _metrics_instance

def reset_metrics():
    """Reset the global metrics instance"""
    global _metrics_instance
    _metrics_instance = SetupMetrics()