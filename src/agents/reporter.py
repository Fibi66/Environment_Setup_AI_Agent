from typing import Dict, Any
import json
from datetime import datetime
from .base import BaseAgent
from ..core.metrics import get_metrics
from ..core.errors import ErrorTracker


class ReporterAgent(BaseAgent):
    def __init__(self, config):
        super().__init__("Reporter", "Report Generation", config)
        self.report_style = config.reporting.get('style', 'concise')
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("📊 Generating report...")
        
        # Collect key information
        report_data = self._collect_report_data(state)
        
        # Generate report based on style
        if self.report_style == 'concise':
            report = await self._generate_concise_report(report_data)
        else:
            report = await self._generate_detailed_report(report_data)
        
        # Save report
        report_path = self._save_report(report, state.get('project_path', '.'))
        
        # Update state
        state['report'] = report
        state['report_path'] = report_path
        
        # Display report
        print("\n" + report)
        
        self.log(f"✅ Report saved to: {report_path}")
        
        return state
    
    def _collect_report_data(self, state: Dict) -> Dict:
        # Get metrics and errors
        metrics = state.get('metrics', get_metrics())
        error_tracker = state.get('error_tracker', ErrorTracker())
        
        # Extract key metrics
        steps = state.get('installation_plan', {}).get('steps', [])
        completed = state.get('completed_steps', [])
        failed = state.get('failed_steps', [])
        
        # Calculate timing
        start_time = state.get('start_time', datetime.now())
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Get language-specific metrics
        language_metrics = {}
        for lang in state.get('detected_languages', []):
            lang_metric = metrics.get_language_metrics(lang)
            if lang_metric:
                language_metrics[lang] = lang_metric.to_dict()
        
        return {
            'project_type': state.get('project_type', 'unknown'),
            'detected_stacks': state.get('detected_stacks', []),
            'detected_languages': state.get('detected_languages', []),
            'completed_languages': state.get('completed_languages', []),
            'failed_languages': state.get('failed_languages', []),
            'total_steps': len(steps),
            'completed_steps': len(completed),
            'failed_steps': len(failed),
            'success_rate': metrics.overall_success_rate,
            'health_score': state.get('health_score', 0),
            'duration_seconds': metrics.duration or duration,
            'language_metrics': language_metrics,
            'error_summary': error_tracker.get_summary(),
            'verification_results': state.get('verification_results', []),
            'critical_failures': state.get('verification_analysis', {}).get('critical_failures', []),
            'warnings': state.get('verification_analysis', {}).get('warnings', []),
            'recommendations': state.get('verification_analysis', {}).get('recommendations', []),
            'test_commands': state.get('scan_results', {}).get('test_commands', []),
            'build_commands': state.get('scan_results', {}).get('build_commands', []),
            'entry_points': state.get('scan_results', {}).get('entry_points', [])
        }
    
    async def _generate_concise_report(self, data: Dict) -> str:
        prompt = f"""
Generate a concise setup report that can be read in 30 seconds.

Data:
{data}

Format the report with:
1. Quick status emoji (⚡/✅/⚠️/❌)
2. What was installed (3-5 items max)
3. How to start the project (exact commands)
4. Any critical actions required
5. Quick summary metrics

Use markdown, emojis for visual scanning, and be EXTREMELY concise.
Focus on what the user needs to know RIGHT NOW to use the project.
Maximum 500 characters.
"""
        
        report = await self.think(prompt)
        
        # Add header and footer
        header = "# ⚡ Setup Complete\n\n"
        
        # Format duration
        duration = data['duration_seconds']
        if duration < 60:
            time_str = f"{int(duration)}s"
        else:
            time_str = f"{int(duration/60)}m {int(duration%60)}s"
        
        footer = f"\n---\n💡 Time: {time_str} | Health: {data['health_score']}%"
        
        return header + report + footer
    
    async def _generate_detailed_report(self, data: Dict) -> str:
        prompt = f"""
Generate a detailed setup report.

Data:
{data}

Include:
1. Installation summary
2. Installed components
3. Verification results
4. How to use the project
5. Troubleshooting tips
6. Next steps

Use markdown formatting.
"""
        
        return await self.think(prompt)
    
    def _save_report(self, report: str, project_path: str) -> str:
        # Create reports directory
        import os
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = os.path.basename(project_path) or "project"
        filename = f"{reports_dir}/setup_{project_name}_{timestamp}.md"
        
        # Save report with UTF-8 encoding
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Also export metrics as JSON
        metrics = state.get('metrics', get_metrics())
        metrics.complete()  # Mark the end of setup
        metrics_file = metrics.export_json(f"{reports_dir}/metrics_{project_name}_{timestamp}.json")
        self.log(f"📈 Metrics exported to: {metrics_file}")
        
        # Export error report if there are errors
        error_tracker = state.get('error_tracker', ErrorTracker())
        if error_tracker.errors:
            error_file = f"{reports_dir}/errors_{project_name}_{timestamp}.json"
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(error_tracker.to_list(), f, indent=2)
            self.log(f"⚠️ Error report saved to: {error_file}")
        
        return filename