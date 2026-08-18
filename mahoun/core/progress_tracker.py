"""
Advanced Progress Tracker with ETA Calculation
==============================================

Real-time progress tracking with estimated time remaining for long-running operations.

Features:
- ETA calculation based on historical speed
- Checkpoint/resume support
- Memory-efficient streaming
- Thread-safe operations

Usage:
    tracker = ProgressTracker(total=1000, description="Processing documents")
    
    for item in items:
        # Do work
        tracker.update(1)
        print(f"Progress: {tracker.percentage:.1f}% | ETA: {tracker.eta_human}")
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


@dataclass
class ProgressSnapshot:
    """Immutable progress snapshot for checkpointing"""
    current: int
    total: int
    start_time: float
    elapsed_seconds: float
    speed: float  # items per second
    eta_seconds: Optional[float]
    percentage: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ProgressTracker:
    """
    Thread-safe progress tracker with ETA calculation.
    
    Automatically calculates:
    - Current progress percentage
    - Processing speed (items/second)
    - Estimated time remaining (ETA)
    - Total elapsed time
    """
    
    def __init__(
        self,
        total: int,
        description: str = "Progress",
        checkpoint_path: Optional[Path] = None,
        update_interval: float = 0.1  # seconds between updates
    ):
        """
        Initialize progress tracker.
        
        Args:
            total: Total number of items to process
            description: Description of the task
            checkpoint_path: Path to save/load checkpoint
            update_interval: Minimum seconds between progress updates
        """
        self.total = total
        self.description = description
        self.checkpoint_path = checkpoint_path
        self.update_interval = update_interval
        
        self._current = 0
        self._start_time = time.time()
        self._last_update_time = 0.0
        self._lock = Lock()
        
        # Speed calculation (exponential moving average)
        self._ema_alpha = 0.1  # Weight for new samples
        self._speed_ema = 0.0  # Exponential moving average of speed
        
        # Load checkpoint if exists
        if checkpoint_path and checkpoint_path.exists():
            self._load_checkpoint()
    
    @property
    def current(self) -> int:
        """Current progress count"""
        with self._lock:
            return self._current
    
    @property
    def elapsed_seconds(self) -> float:
        """Elapsed time in seconds"""
        return time.time() - self._start_time
    
    @property
    def percentage(self) -> float:
        """Progress percentage (0-100)"""
        if self.total == 0:
            return 100.0
        with self._lock:
            return (self._current / self.total) * 100.0
    
    @property
    def speed(self) -> float:
        """Processing speed in items per second"""
        elapsed = self.elapsed_seconds
        if elapsed < 0.1:  # Avoid division by zero
            return 0.0
        with self._lock:
            return self._current / elapsed
    
    @property
    def eta_seconds(self) -> Optional[float]:
        """Estimated time remaining in seconds"""
        if self.total == 0:
            return 0.0
        
        with self._lock:
            remaining = self.total - self._current
            if remaining <= 0:
                return 0.0
            
            # Use EMA speed if available, otherwise instantaneous
            speed = self._speed_ema if self._speed_ema > 0 else self.speed
            if speed <= 0:
                return None
            
            return remaining / speed
    
    @property
    def eta_human(self) -> str:
        """Human-readable ETA string"""
        eta = self.eta_seconds
        if eta is None:
            return "calculating..."
        if eta < 1:
            return "< 1 second"
        
        delta = timedelta(seconds=int(eta))
        
        # Format nicely
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    @property
    def elapsed_human(self) -> str:
        """Human-readable elapsed time string"""
        elapsed = int(self.elapsed_seconds)
        delta = timedelta(seconds=elapsed)
        
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    def update(self, n: int = 1) -> bool:
        """
        Update progress by n items.
        
        Args:
            n: Number of items processed
        
        Returns:
            True if progress was updated (respects update_interval)
        """
        with self._lock:
            self._current = min(self._current + n, self.total)
            
            # Update speed EMA
            current_speed = self.speed
            if self._speed_ema == 0:
                self._speed_ema = current_speed
            else:
                self._speed_ema = (
                    self._ema_alpha * current_speed +
                    (1 - self._ema_alpha) * self._speed_ema
                )
            
            # Check if we should emit update
            now = time.time()
            should_update = (now - self._last_update_time) >= self.update_interval
            
            if should_update:
                self._last_update_time = now
                return True
            
            return False
    
    def set_progress(self, current: int) -> None:
        """Set progress to specific value"""
        with self._lock:
            self._current = min(max(0, current), self.total)
    
    def is_complete(self) -> bool:
        """Check if progress is complete"""
        with self._lock:
            return self._current >= self.total
    
    def snapshot(self) -> ProgressSnapshot:
        """Get immutable snapshot of current progress"""
        return ProgressSnapshot(
            current=self.current,
            total=self.total,
            start_time=self._start_time,
            elapsed_seconds=self.elapsed_seconds,
            speed=self.speed,
            eta_seconds=self.eta_seconds,
            percentage=self.percentage
        )
    
    def save_checkpoint(self) -> None:
        """Save current progress to checkpoint file"""
        if not self.checkpoint_path:
            return
        
        snapshot = self.snapshot()
        checkpoint_data = {
            "description": self.description,
            "current": snapshot.current,
            "total": snapshot.total,
            "timestamp": snapshot.timestamp,
            "elapsed_seconds": snapshot.elapsed_seconds,
            "percentage": snapshot.percentage
        }
        
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        logger.info(f"Checkpoint saved: {snapshot.current}/{snapshot.total} ({snapshot.percentage:.1f}%)")
    
    def _load_checkpoint(self) -> None:
        """Load progress from checkpoint file"""
        try:
            with open(self.checkpoint_path, 'r') as f:
                data = json.load(f)
            
            self._current = data.get("current", 0)
            logger.info(
                f"Checkpoint loaded: resuming from {self._current}/{self.total} "
                f"({self.percentage:.1f}%)"
            )
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
    
    def format_progress_bar(self, width: int = 50) -> str:
        """
        Generate ASCII progress bar.
        
        Args:
            width: Width of progress bar in characters
        
        Returns:
            Formatted progress bar string
        """
        filled = int(width * self.percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        
        return (
            f"{self.description}: |{bar}| "
            f"{self.percentage:.1f}% "
            f"({self.current}/{self.total}) "
            f"[{self.speed:.1f} items/s] "
            f"ETA: {self.eta_human}"
        )
    
    def log_progress(self, level: int = logging.INFO) -> None:
        """Log current progress"""
        logger.log(level, self.format_progress_bar())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "description": self.description,
            "current": self.current,
            "total": self.total,
            "percentage": self.percentage,
            "elapsed_seconds": self.elapsed_seconds,
            "elapsed_human": self.elapsed_human,
            "speed": self.speed,
            "eta_seconds": self.eta_seconds,
            "eta_human": self.eta_human,
            "is_complete": self.is_complete()
        }


class MultiProgressTracker:
    """
    Track multiple concurrent progress bars.
    
    Useful for parallel processing or multi-stage pipelines.
    """
    
    def __init__(self):
        self._trackers: Dict[str, ProgressTracker] = {}
        self._lock = Lock()
    
    def add_tracker(
        self,
        name: str,
        total: int,
        description: Optional[str] = None
    ) -> ProgressTracker:
        """Add a new progress tracker"""
        with self._lock:
            tracker = ProgressTracker(
                total=total,
                description=description or name
            )
            self._trackers[name] = tracker
            return tracker
    
    def get_tracker(self, name: str) -> Optional[ProgressTracker]:
        """Get tracker by name"""
        with self._lock:
            return self._trackers.get(name)
    
    def remove_tracker(self, name: str) -> None:
        """Remove tracker"""
        with self._lock:
            self._trackers.pop(name, None)
    
    def snapshot_all(self) -> Dict[str, ProgressSnapshot]:
        """Get snapshots of all trackers"""
        with self._lock:
            return {
                name: tracker.snapshot()
                for name, tracker in self._trackers.items()
            }
    
    def total_percentage(self) -> float:
        """Calculate overall percentage across all trackers"""
        with self._lock:
            if not self._trackers:
                return 0.0
            
            total_progress = sum(t.current for t in self._trackers.values())
            total_items = sum(t.total for t in self._trackers.values())
            
            if total_items == 0:
                return 0.0
            
            return (total_progress / total_items) * 100.0
    
    def format_summary(self) -> str:
        """Format summary of all trackers"""
        lines = ["Progress Summary:"]
        lines.append("=" * 60)
        
        with self._lock:
            for name, tracker in self._trackers.items():
                lines.append(
                    f"  {name}: {tracker.percentage:.1f}% "
                    f"({tracker.current}/{tracker.total}) "
                    f"ETA: {tracker.eta_human}"
                )
        
        lines.append("=" * 60)
        lines.append(f"Overall: {self.total_percentage():.1f}%")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        with self._lock:
            return {
                "trackers": {
                    name: tracker.to_dict()
                    for name, tracker in self._trackers.items()
                },
                "total_percentage": self.total_percentage()
            }
