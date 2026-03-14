import re
from pathlib import Path
from typing import Dict

def extract_metadata(file_path: Path) -> Dict[str, str]:
    """Parses implementation_request.md for specific metadata fields."""
    content = file_path.read_text(encoding='utf-8')
    
    metadata = {}
    patterns = {
        'id': r'ID:\s*(IRQ-[\w-]+)',
        'repo': r'Repo:\s*([\w\-\./:]+)',
        'base_commit': r'Base Commit:\s*([a-f0-9]+|TBD)',
        'feature_branch': r'Feature Branch:\s*([\w\-/]+)'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            metadata[key] = match.group(1).strip()
        else:
            raise ValueError(f"Missing required metadata: {key}")
            
    return metadata
