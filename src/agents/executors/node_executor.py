import asyncio
import platform
import time
from typing import Dict, Any
from ..base import BaseAgent
from ...core.metrics import get_metrics
from ...core.errors import SetupError, ErrorType, ErrorSeverity, ErrorTracker


class NodeExecutor(BaseAgent):
    def __init__(self, config):
        super().__init__("NodeExecutor", "Node.js Environment Setup", config)
        self.metrics = get_metrics()
        self.error_tracker = ErrorTracker()
        
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("🟢 Setting up Node.js environment...")
        
        # Start metrics tracking
        lang_metrics = self.metrics.add_language('nodejs')
        lang_metrics.start()
        
        config = state.get('language_configs', {}).get('nodejs', {})
        project_path = state.get('project_path', '.')
        
        # Check if Node.js is installed
        node_installed = await self._check_node_installed()
        
        if not node_installed:
            self.log("📦 Installing Node.js...")
            success = await self._install_nodejs()
            if not success:
                error = SetupError(
                    error_type=ErrorType.INSTALLATION_FAILED,
                    message="Failed to install Node.js",
                    severity=ErrorSeverity.HIGH,
                    agent="NodeExecutor",
                    language="nodejs"
                )
                self.error_tracker.add_error(error)
                self.log("❌ Failed to install Node.js")
                state['failed_languages'].append('nodejs')
                lang_metrics.complete(success=False)
                self._update_state_errors(state)
                return state
        
        # Install dependencies if package.json exists
        if config.get('has_package_json'):
            package_manager = config.get('package_manager', 'npm')
            self.log(f"📦 Installing dependencies with {package_manager}...")
            
            success = await self._install_dependencies(project_path, package_manager)
            if not success:
                error = SetupError(
                    error_type=ErrorType.DEPENDENCY_CONFLICT,
                    message=f"Failed to install dependencies with {package_manager}",
                    severity=ErrorSeverity.MEDIUM,
                    agent="NodeExecutor",
                    language="nodejs",
                    command=f"{package_manager} install"
                )
                self.error_tracker.add_error(error)
                self.log(f"❌ Failed to install dependencies")
                state['failed_languages'].append('nodejs')
                lang_metrics.complete(success=False)
                self._update_state_errors(state)
                return state
        
        # Mark as completed
        state['completed_languages'].append('nodejs')
        lang_metrics.complete(success=True)
        self.log("✅ Node.js environment setup complete")
        
        # Update state with metrics
        self._update_state_metrics(state)
        
        return state
    
    async def _check_node_installed(self) -> bool:
        """Check if Node.js is installed"""
        try:
            process = await asyncio.create_subprocess_shell(
                "node --version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                version = stdout.decode().strip()
                self.log(f"✓ Node.js detected: {version}")
                return True
            return False
        except:
            return False
    
    async def _install_nodejs(self) -> bool:
        """Install Node.js based on OS"""
        system = platform.system()
        
        if system == "Windows":
            # Windows installation
            commands = [
                "winget install OpenJS.NodeJS --accept-package-agreements --accept-source-agreements"
            ]
        else:  # Ubuntu/Linux
            # Ubuntu installation
            commands = [
                "curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -",
                "sudo apt-get install -y nodejs"
            ]
        
        for cmd in commands:
            self.log(f"  Running: {cmd[:50]}...")
            cmd_start = time.time()
            try:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=300  # 5 minutes timeout
                )
                cmd_duration = time.time() - cmd_start
                
                if process.returncode != 0:
                    self.log(f"  ⚠️ Command failed: {stderr.decode()[:200]}")
                    lang_metrics = self.metrics.get_language_metrics('nodejs')
                    if lang_metrics:
                        lang_metrics.add_command(cmd, False, cmd_duration)
                    return False
                else:
                    lang_metrics = self.metrics.get_language_metrics('nodejs')
                    if lang_metrics:
                        lang_metrics.add_command(cmd, True, cmd_duration)
            except asyncio.TimeoutError:
                self.log("  ⚠️ Installation timeout")
                error = SetupError(
                    error_type=ErrorType.TIMEOUT,
                    message="Node.js installation timeout after 5 minutes",
                    severity=ErrorSeverity.HIGH,
                    agent="NodeExecutor",
                    language="nodejs",
                    command=cmd
                )
                self.error_tracker.add_error(error)
                return False
            except Exception as e:
                self.log(f"  ⚠️ Error: {str(e)}")
                error = SetupError.from_exception(e, "NodeExecutor", "nodejs", cmd)
                self.error_tracker.add_error(error)
                return False
        
        return True
    
    async def _install_dependencies(self, project_path: str, package_manager: str) -> bool:
        """Install Node.js dependencies"""
        # Determine install command
        if package_manager == "yarn":
            install_cmd = "yarn install"
        else:
            install_cmd = "npm install"
        
        try:
            self.log(f"  Running: {install_cmd}")
            process = await asyncio.create_subprocess_shell(
                install_cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600  # 10 minutes timeout for large projects
            )
            
            if process.returncode == 0:
                self.log("  ✓ Dependencies installed successfully")
                return True
            else:
                error_msg = stderr.decode()[:500]
                self.log(f"  ⚠️ Installation failed: {error_msg}")
                
                # Try to recover with common fixes
                if "EACCES" in error_msg or "permission" in error_msg.lower():
                    self.log("  🔧 Retrying with permission fixes...")
                    if platform.system() != "Windows":
                        # Fix npm permissions on Linux
                        fix_cmd = "sudo npm install -g npm"
                        await self._run_command(fix_cmd)
                        return await self._install_dependencies(project_path, package_manager)
                
                return False
                
        except asyncio.TimeoutError:
            self.log("  ⚠️ Installation timeout after 10 minutes")
            return False
        except Exception as e:
            self.log(f"  ⚠️ Error: {str(e)}")
            return False
    
    async def _run_command(self, cmd: str) -> bool:
        """Helper to run a command"""
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except:
            return False
    
    def _update_state_errors(self, state: Dict[str, Any]):
        """Update state with error information"""
        if 'error_tracker' not in state:
            state['error_tracker'] = self.error_tracker
        else:
            # Merge errors
            for error in self.error_tracker.errors:
                state['error_tracker'].add_error(error)
    
    def _update_state_metrics(self, state: Dict[str, Any]):
        """Update state with metrics information"""
        if 'metrics' not in state:
            state['metrics'] = self.metrics
        # Metrics are already updated in the global instance