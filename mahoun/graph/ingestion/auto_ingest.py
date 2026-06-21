#!/usr/bin/env python3
"""
Automated Document Ingestion
=============================
Watches for new files and automatically ingests them
"""

import time
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)


class DocumentIngestHandler(FileSystemEventHandler):
    """File system event handler for document ingestion"""
    
    def __init__(self, ingest_callback):
        self.ingest_callback = ingest_callback
        self.processing = set()
    
    def on_created(self, event):
        """Handle new file creation"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Check file extension
        if file_path.suffix.lower() not in ['.json', '.txt', '.pdf', '.docx']:
            return
        
        # Avoid duplicate processing
        if str(file_path) in self.processing:
            return
        
        log.info(f"New file detected: {file_path}")
        
        # Wait for file to be fully written
        time.sleep(1)
        
        try:
            self.processing.add(str(file_path))
            self.ingest_callback(file_path)
        except Exception as e:
            log.error(f"Failed to ingest {file_path}: {e}")
        finally:
            self.processing.discard(str(file_path))


class AutoIngestService:
    """
    Automated document ingestion service
    
    Watches a directory for new files and automatically ingests them
    """
    
    def __init__(
        self,
        watch_dir: str = "/data/raw",
        ingest_callback: Optional[callable] = None
    ):
        """
        Initialize auto-ingest service
        
        Args:
            watch_dir: Directory to watch
            ingest_callback: Function to call for ingestion
        """
        self.watch_dir = Path(watch_dir)
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        
        self.ingest_callback = ingest_callback or self._default_ingest
        self.observer = None
        
        log.info(f"AutoIngestService initialized: {self.watch_dir}")
    
    def _default_ingest(self, file_path: Path):
        """Default ingestion handler"""
        log.info(f"Ingesting: {file_path}")
        
        # Read file
        if file_path.suffix == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = {"text": f.read(), "source": str(file_path)}
        
        # TODO: Process and store in database
        log.info(f"Ingested: {file_path.name}")
    
    def start(self):
        """Start watching directory"""
        if self.observer:
            log.warning("Service already running")
            return
        
        event_handler = DocumentIngestHandler(self.ingest_callback)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.watch_dir), recursive=False)
        self.observer.start()
        
        log.info(f"Started watching: {self.watch_dir}")
    
    def stop(self):
        """Stop watching directory"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            log.info("Stopped watching")
    
    def run(self):
        """Run service (blocking)"""
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    service = AutoIngestService()
    service.run()
