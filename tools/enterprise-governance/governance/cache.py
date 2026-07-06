from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import ast

from .model import ProjectModel


class FileCache:
    """Cache for storing file analysis results."""
    
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "analysis_cache.json"
        self._cache: Dict[str, Any] = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                return json.loads(self.cache_file.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        self.cache_file.write_text(json.dumps(self._cache, indent=2))
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Get hash of file content."""
        try:
            content = file_path.read_bytes()
            return hashlib.sha256(content).hexdigest()
        except OSError:
            return ""
    
    def get_cached_ast(self, file_path: Path) -> Optional[ast.Module]:
        """Get cached AST for a file if it hasn't changed."""
        file_key = str(file_path)
        current_hash = self._get_file_hash(file_path)
        
        if file_key in self._cache:
            cached_entry = self._cache[file_key]
            if cached_entry.get("hash") == current_hash:
                # Reconstruct AST from cached source
                try:
                    return ast.parse(cached_entry["source"])
                except (SyntaxError, KeyError):
                    pass
        
        return None
    
    def cache_ast(self, file_path: Path, tree: ast.Module) -> None:
        """Cache AST for a file."""
        file_key = str(file_path)
        try:
            source = file_path.read_text(encoding="utf-8")
            self._cache[file_key] = {
                "hash": self._get_file_hash(file_path),
                "source": source
            }
            self._save_cache()
        except OSError:
            pass  # Skip caching if we can't read the file
    
    def is_file_changed(self, file_path: Path) -> bool:
        """Check if a file has changed since last cached."""
        file_key = str(file_path)
        current_hash = self._get_file_hash(file_path)
        
        if file_key not in self._cache:
            return True
            
        return self._cache[file_key].get("hash") != current_hash
    
    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        if self.cache_file.exists():
            self.cache_file.unlink()


class IncrementalParser:
    """Parser that uses caching to avoid re-parsing unchanged files."""
    
    def __init__(self, project_model: ProjectModel, cache_dir: Optional[Path] = None) -> None:
        self.model = project_model
        self.cache = FileCache(cache_dir or (project_model.root_path / ".govcache"))
    
    def parse_all(self) -> None:
        """Parse all files, using cache for unchanged files."""
        for file_path in self.model.files:
            # Try to get cached AST first
            cached_tree = self.cache.get_cached_ast(file_path)
            
            if cached_tree is not None:
                # Use cached AST
                self.model.ast_forest[file_path] = cached_tree
            else:
                # Parse and cache
                try:
                    content = file_path.read_text(encoding="utf-8")
                    tree = ast.parse(content)
                    self.model.ast_forest[file_path] = tree
                    self.cache.cache_ast(file_path, tree)
                except (SyntaxError, UnicodeDecodeError) as e:
                    # Store error in metadata
                    self.model.metadata.setdefault("parse_errors", []).append({
                        "file": str(file_path),
                        "error": str(e)
                    })
    
    def get_ast(self, file_path: Path) -> Optional[ast.Module]:
        """Get AST for a file, using cache if available."""
        cached_tree = self.cache.get_cached_ast(file_path)
        if cached_tree is not None:
            return cached_tree
            
        # If not in cache, try to parse
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            self.cache.cache_ast(file_path, tree)
            return tree
        except (SyntaxError, UnicodeDecodeError):
            return None
    
    def clear_cache(self) -> None:
        """Clear the parser cache."""
        self.cache.clear()