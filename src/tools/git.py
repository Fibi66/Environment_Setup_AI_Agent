import os
from typing import Optional, Dict, Any
from .shell import ShellExecutor


class GitTools:
    def __init__(self):
        self.shell = ShellExecutor()
    
    def is_git_repo(self, path: str) -> bool:
        return os.path.exists(os.path.join(path, '.git'))
    
    def get_repo_info(self, path: str) -> Dict[str, Any]:
        if not self.is_git_repo(path):
            return {}
        
        info = {}
        
        # Get remote URL
        code, stdout, _ = self.shell.execute_sync('git remote get-url origin', cwd=path)
        if code == 0:
            info['remote_url'] = stdout.strip()
        
        # Get current branch
        code, stdout, _ = self.shell.execute_sync('git branch --show-current', cwd=path)
        if code == 0:
            info['branch'] = stdout.strip()
        
        # Get last commit
        code, stdout, _ = self.shell.execute_sync('git log -1 --oneline', cwd=path)
        if code == 0:
            info['last_commit'] = stdout.strip()
        
        return info
    
    def clone(self, url: str, target: str) -> bool:
        code, _, _ = self.shell.execute_sync(f'git clone {url} {target}')
        return code == 0