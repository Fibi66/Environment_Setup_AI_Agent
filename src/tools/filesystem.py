import os
from pathlib import Path
from typing import List, Optional


class FileSystem:
    def scan_directory(self, path: str, max_files: int = 1000) -> List[str]:
        files = []
        path = Path(path)
        
        if not path.exists():
            return files
        
        for root, dirs, filenames in os.walk(path):
            # Skip hidden and vendor directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__']]
            
            for filename in filenames:
                if not filename.startswith('.'):
                    files.append(str(Path(root) / filename))
                    
                if len(files) >= max_files:
                    return files
        
        return files
    
    def read_file(self, path: str, max_size: int = 100000) -> Optional[str]:
        try:
            path = Path(path)
            if path.exists() and path.stat().st_size <= max_size:
                return path.read_text()
        except Exception:
            pass
        return None
    
    def write_file(self, path: str, content: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content)
    
    def file_exists(self, path: str) -> bool:
        return Path(path).exists()
    
    def get_file_info(self, path: str) -> dict:
        p = Path(path)
        if not p.exists():
            return {}
        
        stat = p.stat()
        return {
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'is_file': p.is_file(),
            'is_dir': p.is_dir(),
            'extension': p.suffix
        }