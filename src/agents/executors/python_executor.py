import asyncio
import platform
import os
from typing import Dict, Any
from pathlib import Path
from ..base import BaseAgent


class PythonExecutor(BaseAgent):
    def __init__(self, config):
        super().__init__("PythonExecutor", "Python Environment Setup", config)
        
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("🐍 Setting up Python environment...")
        
        config = state.get('language_configs', {}).get('python', {})
        project_path = state.get('project_path', '.')
        
        # Check if Python is installed
        python_cmd = await self._get_python_command()
        if not python_cmd:
            self.log("📦 Installing Python...")
            success = await self._install_python()
            if not success:
                self.log("❌ Failed to install Python")
                state['failed_languages'].append('python')
                return state
            python_cmd = await self._get_python_command()
        
        # Create virtual environment
        venv_path = os.path.join(project_path, 'venv')
        if config.get('use_venv', True) and not os.path.exists(venv_path):
            self.log("🔧 Creating virtual environment...")
            success = await self._create_venv(project_path, python_cmd)
            if not success:
                self.log("⚠️ Failed to create virtual environment, continuing without it")
        
        # Install dependencies
        dep_files = []
        if config.get('has_requirements'):
            dep_files.append('requirements.txt')
        if config.get('has_pipfile'):
            dep_files.append('Pipfile')
        if config.get('has_pyproject'):
            dep_files.append('pyproject.toml')
        
        if dep_files:
            self.log(f"📦 Installing dependencies from: {', '.join(dep_files)}")
            for dep_file in dep_files:
                success = await self._install_dependencies(project_path, dep_file, python_cmd)
                if not success:
                    self.log(f"⚠️ Failed to install from {dep_file}")
        
        # Install setup.py if exists
        if config.get('has_setup_py'):
            self.log("📦 Installing package from setup.py...")
            await self._install_setup_py(project_path, python_cmd)
        
        # Mark as completed
        state['completed_languages'].append('python')
        self.log("✅ Python environment setup complete")
        
        return state
    
    async def _get_python_command(self) -> str:
        """Find the correct Python command"""
        commands = ['python3', 'python', 'py']
        
        for cmd in commands:
            try:
                process = await asyncio.create_subprocess_shell(
                    f"{cmd} --version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    version = stdout.decode().strip() or stderr.decode().strip()
                    self.log(f"✓ Python detected: {version}")
                    return cmd
            except:
                continue
        
        return None
    
    async def _install_python(self) -> bool:
        """Install Python based on OS"""
        system = platform.system()
        
        if system == "Windows":
            # Windows installation
            commands = [
                "winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements"
            ]
        else:  # Ubuntu/Linux
            # Ubuntu installation
            commands = [
                "sudo apt-get update",
                "sudo apt-get install -y python3 python3-pip python3-venv"
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
                    timeout=300
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
    
    async def _create_venv(self, project_path: str, python_cmd: str) -> bool:
        """Create virtual environment"""
        venv_path = os.path.join(project_path, 'venv')
        
        try:
            cmd = f"{python_cmd} -m venv venv"
            self.log(f"  Running: {cmd}")
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60
            )
            
            if process.returncode == 0:
                self.log("  ✓ Virtual environment created")
                return True
            else:
                self.log(f"  ⚠️ Failed: {stderr.decode()[:200]}")
                return False
                
        except Exception as e:
            self.log(f"  ⚠️ Error: {str(e)}")
            return False
    
    async def _install_dependencies(self, project_path: str, dep_file: str, python_cmd: str) -> bool:
        """Install Python dependencies"""
        # Determine pip command - use venv if it exists
        venv_path = os.path.join(project_path, 'venv')
        if os.path.exists(venv_path):
            if platform.system() == "Windows":
                pip_cmd = os.path.join(venv_path, 'Scripts', 'pip')
            else:
                pip_cmd = os.path.join(venv_path, 'bin', 'pip')
        else:
            pip_cmd = f"{python_cmd} -m pip"
        
        # Build install command based on file type
        if dep_file == 'requirements.txt':
            install_cmd = f"{pip_cmd} install -r requirements.txt"
        elif dep_file == 'Pipfile':
            # Install pipenv first if needed
            await self._run_command(f"{pip_cmd} install pipenv")
            install_cmd = "pipenv install"
        elif dep_file == 'pyproject.toml':
            # For pyproject.toml, try to install with pip
            install_cmd = f"{pip_cmd} install ."
        else:
            return False
        
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
                timeout=600  # 10 minutes timeout
            )
            
            if process.returncode == 0:
                self.log(f"  ✓ Dependencies from {dep_file} installed")
                return True
            else:
                error_msg = stderr.decode()[:500]
                self.log(f"  ⚠️ Installation failed: {error_msg}")
                
                # Try to upgrade pip and retry
                if "pip" in error_msg.lower() or "upgrade" in error_msg.lower():
                    self.log("  🔧 Upgrading pip and retrying...")
                    await self._run_command(f"{pip_cmd} install --upgrade pip")
                    return await self._install_dependencies(project_path, dep_file, python_cmd)
                
                return False
                
        except asyncio.TimeoutError:
            self.log("  ⚠️ Installation timeout after 10 minutes")
            return False
        except Exception as e:
            self.log(f"  ⚠️ Error: {str(e)}")
            return False
    
    async def _install_setup_py(self, project_path: str, python_cmd: str) -> bool:
        """Install package from setup.py"""
        venv_path = os.path.join(project_path, 'venv')
        if os.path.exists(venv_path):
            if platform.system() == "Windows":
                pip_cmd = os.path.join(venv_path, 'Scripts', 'pip')
            else:
                pip_cmd = os.path.join(venv_path, 'bin', 'pip')
        else:
            pip_cmd = f"{python_cmd} -m pip"
        
        cmd = f"{pip_cmd} install -e ."
        return await self._run_command_in_dir(cmd, project_path)
    
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
    
    async def _run_command_in_dir(self, cmd: str, cwd: str) -> bool:
        """Helper to run a command in a directory"""
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except:
            return False