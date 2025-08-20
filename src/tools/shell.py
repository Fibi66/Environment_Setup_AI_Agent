import asyncio
import subprocess
from typing import Tuple, Optional


class ShellExecutor:
    async def execute(
        self, 
        command: str, 
        cwd: str = '.', 
        timeout: int = 300,
        env: Optional[dict] = None
    ) -> Tuple[int, str, str]:
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return (
                process.returncode,
                stdout.decode() if stdout else '',
                stderr.decode() if stderr else ''
            )
            
        except asyncio.TimeoutError:
            return (-1, '', f'Command timed out after {timeout} seconds')
        except Exception as e:
            return (-1, '', str(e))
    
    def execute_sync(
        self, 
        command: str, 
        cwd: str = '.', 
        timeout: int = 300
    ) -> Tuple[int, str, str]:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout
            )
            
            return (result.returncode, result.stdout, result.stderr)
            
        except subprocess.TimeoutExpired:
            return (-1, '', f'Command timed out after {timeout} seconds')
        except Exception as e:
            return (-1, '', str(e))