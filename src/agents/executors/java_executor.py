import asyncio
import platform
import os
import time
from typing import Dict, Any
from ..base import BaseAgent
from ...core.metrics import get_metrics
from ...core.errors import SetupError, ErrorType, ErrorSeverity, ErrorTracker


class JavaExecutor(BaseAgent):
    def __init__(self, config):
        super().__init__("JavaExecutor", "Java Environment Setup", config)
        self.metrics = get_metrics()
        self.error_tracker = ErrorTracker()
        
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.log("☕ Setting up Java environment...")
        
        # Get metrics and error tracker from state
        self.metrics = state.get('metrics', get_metrics())
        self.error_tracker = state.get('error_tracker', ErrorTracker())
        
        # Start metrics tracking
        lang_metrics = self.metrics.add_language('java')
        lang_metrics.start()
        
        config = state.get('language_configs', {}).get('java', {})
        project_path = state.get('project_path', '.')
        build_tool = config.get('build_tool', 'maven')
        
        # Check if Java is installed
        java_installed = await self._check_java_installed()
        if not java_installed:
            self.log("📦 Installing Java JDK...")
            success = await self._install_java()
            if not success:
                error = SetupError(
                    error_type=ErrorType.INSTALLATION_FAILED,
                    message="Failed to install Java JDK",
                    severity=ErrorSeverity.HIGH,
                    agent="JavaExecutor",
                    language="java"
                )
                self.error_tracker.add_error(error)
                self.log("❌ Failed to install Java")
                state['failed_languages'].append('java')
                lang_metrics.complete(success=False)
                return state
        
        # Install build tool if needed
        if build_tool == 'maven' and config.get('has_pom'):
            maven_installed = await self._check_maven_installed()
            if not maven_installed:
                self.log("📦 Installing Maven...")
                success = await self._install_maven()
                if not success:
                    self.log("❌ Failed to install Maven")
                    state['failed_languages'].append('java')
                    return state
            
            # Run maven install
            self.log("📦 Installing Maven dependencies...")
            success = await self._run_maven_install(project_path)
            if not success:
                self.log("⚠️ Maven dependency installation had issues")
        
        elif build_tool == 'gradle' and config.get('has_gradle'):
            gradle_installed = await self._check_gradle_installed()
            if not gradle_installed:
                self.log("📦 Installing Gradle...")
                success = await self._install_gradle()
                if not success:
                    self.log("❌ Failed to install Gradle")
                    state['failed_languages'].append('java')
                    return state
            
            # Run gradle build
            self.log("📦 Building with Gradle...")
            success = await self._run_gradle_build(project_path)
            if not success:
                self.log("⚠️ Gradle build had issues")
        
        # Set JAVA_HOME if not set
        await self._set_java_home()
        
        # Mark as completed
        state['completed_languages'].append('java')
        lang_metrics.complete(success=True)
        self.log("✅ Java environment setup complete")
        
        return state
    
    async def _check_java_installed(self) -> bool:
        """Check if Java is installed"""
        try:
            process = await asyncio.create_subprocess_shell(
                "java -version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Java outputs version to stderr
                version = stderr.decode().strip() if stderr else stdout.decode().strip()
                self.log(f"✓ Java detected: {version.split('\\n')[0]}")
                return True
            return False
        except:
            return False
    
    async def _check_maven_installed(self) -> bool:
        """Check if Maven is installed"""
        try:
            process = await asyncio.create_subprocess_shell(
                "mvn --version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return process.returncode == 0
        except:
            return False
    
    async def _check_gradle_installed(self) -> bool:
        """Check if Gradle is installed"""
        try:
            process = await asyncio.create_subprocess_shell(
                "gradle --version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return process.returncode == 0
        except:
            return False
    
    async def _install_java(self) -> bool:
        """Install Java JDK based on OS"""
        system = platform.system()
        
        if system == "Windows":
            # Windows installation - try OpenJDK first
            commands = [
                "winget install Microsoft.OpenJDK.17 --accept-package-agreements --accept-source-agreements"
            ]
        else:  # Ubuntu/Linux
            # Ubuntu installation
            commands = [
                "sudo apt-get update",
                "sudo apt-get install -y openjdk-17-jdk"
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
    
    async def _install_maven(self) -> bool:
        """Install Maven based on OS"""
        system = platform.system()
        
        if system == "Windows":
            commands = [
                "winget install Apache.Maven --accept-package-agreements --accept-source-agreements"
            ]
        else:  # Ubuntu/Linux
            commands = [
                "sudo apt-get install -y maven"
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
            except Exception as e:
                self.log(f"  ⚠️ Error: {str(e)}")
                return False
        
        return True
    
    async def _install_gradle(self) -> bool:
        """Install Gradle based on OS"""
        system = platform.system()
        
        if system == "Windows":
            commands = [
                "winget install Gradle.Gradle --accept-package-agreements --accept-source-agreements"
            ]
        else:  # Ubuntu/Linux
            commands = [
                "sudo apt-get install -y gradle"
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
                    # Try alternative installation method for Linux
                    if system != "Windows":
                        self.log("  🔧 Trying SDKMAN installation...")
                        alt_commands = [
                            "curl -s 'https://get.sdkman.io' | bash",
                            "source ~/.sdkman/bin/sdkman-init.sh",
                            "sdk install gradle"
                        ]
                        for alt_cmd in alt_commands:
                            await self._run_command(alt_cmd)
                        return True
                    return False
            except Exception as e:
                self.log(f"  ⚠️ Error: {str(e)}")
                return False
        
        return True
    
    async def _run_maven_install(self, project_path: str) -> bool:
        """Run Maven install to download dependencies"""
        try:
            # First clean to ensure fresh start
            clean_cmd = "mvn clean"
            self.log(f"  Running: {clean_cmd}")
            
            process = await asyncio.create_subprocess_shell(
                clean_cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.communicate(), timeout=120)
            
            # Now run install to download dependencies
            install_cmd = "mvn install -DskipTests"
            self.log(f"  Running: {install_cmd}")
            
            process = await asyncio.create_subprocess_shell(
                install_cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=900  # 15 minutes for large projects
            )
            
            if process.returncode == 0:
                self.log("  ✓ Maven dependencies installed")
                return True
            else:
                # Try dependency:resolve as fallback
                self.log("  🔧 Trying mvn dependency:resolve...")
                resolve_cmd = "mvn dependency:resolve"
                process = await asyncio.create_subprocess_shell(
                    resolve_cmd,
                    cwd=project_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=600
                )
                
                if process.returncode == 0:
                    self.log("  ✓ Maven dependencies resolved")
                    return True
                else:
                    self.log(f"  ⚠️ Maven had issues: {stderr.decode()[:300]}")
                    return False
                
        except asyncio.TimeoutError:
            self.log("  ⚠️ Maven timeout after 15 minutes")
            return False
        except Exception as e:
            self.log(f"  ⚠️ Error: {str(e)}")
            return False
    
    async def _run_gradle_build(self, project_path: str) -> bool:
        """Run Gradle build to download dependencies"""
        try:
            # Check if gradlew exists (Gradle wrapper)
            gradlew = "./gradlew" if platform.system() != "Windows" else "gradlew.bat"
            gradlew_path = os.path.join(project_path, gradlew.replace("./", ""))
            
            if os.path.exists(gradlew_path):
                gradle_cmd = gradlew
                # Make gradlew executable on Unix
                if platform.system() != "Windows":
                    chmod_cmd = f"chmod +x {gradlew}"
                    await self._run_command_in_dir(chmod_cmd, project_path)
            else:
                gradle_cmd = "gradle"
            
            # Run gradle build
            build_cmd = f"{gradle_cmd} build -x test"
            self.log(f"  Running: {build_cmd}")
            
            process = await asyncio.create_subprocess_shell(
                build_cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=900  # 15 minutes
            )
            
            if process.returncode == 0:
                self.log("  ✓ Gradle build successful")
                return True
            else:
                # Try just downloading dependencies
                self.log("  🔧 Trying gradle dependencies...")
                deps_cmd = f"{gradle_cmd} dependencies"
                await self._run_command_in_dir(deps_cmd, project_path)
                return True
                
        except asyncio.TimeoutError:
            self.log("  ⚠️ Gradle timeout after 15 minutes")
            return False
        except Exception as e:
            self.log(f"  ⚠️ Error: {str(e)}")
            return False
    
    async def _set_java_home(self) -> bool:
        """Set JAVA_HOME environment variable if not set"""
        if os.environ.get('JAVA_HOME'):
            return True
        
        system = platform.system()
        
        if system == "Windows":
            # Windows JAVA_HOME is usually set by installer
            self.log("  ℹ️ JAVA_HOME should be set by installer")
        else:
            # Try to find Java installation and suggest JAVA_HOME
            try:
                process = await asyncio.create_subprocess_shell(
                    "which java",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                
                if process.returncode == 0:
                    java_path = stdout.decode().strip()
                    # Get the actual Java home (usually two levels up from bin/java)
                    java_home = os.path.dirname(os.path.dirname(os.path.realpath(java_path)))
                    self.log(f"  ℹ️ Suggested JAVA_HOME: {java_home}")
                    self.log(f"     Add to ~/.bashrc: export JAVA_HOME={java_home}")
            except:
                pass
        
        return True
    
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