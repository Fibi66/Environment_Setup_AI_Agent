import asyncio
import platform
from typing import Dict, Any
from ..base import BaseAgent


class NodeExecutor(BaseAgent):
    def __init__(self, config):
        super().__init__("NodeExecutor", "Node.js Environment Setup", config)
        
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("🟢 Setting up Node.js environment...")
        
        config = state.get('language_configs', {}).get('nodejs', {})
        project_path = state.get('project_path', '.')
        
        # Check if Node.js is installed
        node_installed = await self._check_node_installed()
        
        if not node_installed:
            self.log("📦 Installing Node.js...")
            success = await self._install_nodejs()
            if not success:
                self.log("❌ Failed to install Node.js")
                state['failed_languages'].append('nodejs')
                return state
        
        # Install dependencies if package.json exists
        if config.get('has_package_json'):
            package_manager = config.get('package_manager', 'npm')
            self.log(f"📦 Installing dependencies with {package_manager}...")
            
            success = await self._install_dependencies(project_path, package_manager)
            if not success:
                self.log(f"❌ Failed to install dependencies")
                state['failed_languages'].append('nodejs')
                return state
        
        # Mark as completed
        state['completed_languages'].append('nodejs')
        self.log("✅ Node.js environment setup complete")
        
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
                
                if process.returncode != 0:
                    self.log(f"  ⚠️ Command failed: {stderr.decode()[:200]}")
                    return False
            except asyncio.TimeoutError:
                self.log("  ⚠️ Installation timeout")
                return False
            except Exception as e:
                self.log(f"  ⚠️ Error: {str(e)}")
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