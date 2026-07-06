from __future__ import annotations

from .model import Detector
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .model import Finding, ProjectModel


class DetectorRegistry:
    """
    Registry for managing detectors.
    Supports registration, retrieval, and ordering by priority.
    """
    def __init__(self) -> None:
        self._detectors: List[Detector] = []

    def register(self, detector: Detector) -> None:
        """Register a detector."""
        self._detectors.append(detector)

    def unregister(self, name: str) -> bool:
        """Unregister a detector by name. Returns True if found and removed."""
        for i, det in enumerate(self._detectors):
            if det.name == name:
                del self._detectors[i]
                return True
        return False

    def get_detector(self, name: str) -> Detector | None:
        """Get a detector by name."""
        for det in self._detectors:
            if det.name == name:
                return det
        return None

    def get_all_detectors(self) -> List[Detector]:
        """Get all detectors sorted by priority (ascending, then by registration order)."""
        return sorted(self._detectors, key=lambda d: (d.priority, self._detectors.index(d)))

    def clear(self) -> None:
        """Remove all detectors."""
        self._detectors.clear()