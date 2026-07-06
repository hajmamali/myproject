from __future__ import annotations

import concurrent.futures
import os
from pathlib import Path
from typing import Optional
import ast

from .model import ProjectModel
from .parser import ProjectParser


class ParallelParser:
    """Parser that uses parallel processing to parse multiple files concurrently."""
    
    def __init__(self, project_model: ProjectModel, max_workers: Optional[int] = None) -> None:
        self.model = project_model
        # Default to number of CPU workers, but cap it reasonably
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
    
    def parse_all(self) -> None:
        """Parse all files in parallel using a thread pool."""
        # We use threads because file I/O and AST parsing are mostly I/O bound
        # and Python's GIL doesn't severely impact this type of work
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all parsing tasks
            future_to_file = {
                executor.submit(self._parse_file, file_path): file_path
                for file_path in self.model.files
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    tree = future.result()
                    if tree is not None:
                        self.model.ast_forest[file_path] = tree
                except Exception as exc:
                    # Handle parsing errors gracefully
                    # In a production system, we might want to log these
                    pass
    
    def _parse_file(self, file_path: Path) -> Optional[ast.Module]:
        """Parse a single file and return its AST, or None if parsing fails."""
        try:
            # Read file content
            content = file_path.read_text(encoding="utf-8")
            # Parse to AST
            return ast.parse(content)
        except (SyntaxError, UnicodeDecodeError, OSError):
            # Return None for files that can't be parsed
            return None


# For backward compatibility and testing, keep the original Parser class reference
# This allows existing code to continue working
def create_parser(project_model: ProjectModel, use_parallel: bool = True) -> object:
    """
    Factory function to create the appropriate parser based on configuration.
    
    Args:
        project_model: The model to parse files for
        use_parallel: Whether to use parallel parsing (default: True)
        
    Returns:
        A parser instance (either ParallelParser or ProjectParser)
    """
    if use_parallel:
        return ParallelParser(project_model)
    else:
        return ProjectParser(project_model)