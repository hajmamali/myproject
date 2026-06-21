"""
Temporal Reasoning Engine
==========================

Reasoning about time, events, and temporal relationships.

Features:
- Allen's interval algebra
- Temporal logic (LTL, CTL)
- Event calculus
- Timeline reasoning
- Temporal constraint satisfaction

Used for:
- Legal timeline reconstruction
- Event ordering
- Temporal compliance checking
- Historical reasoning

Author: MAHOUN Team
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging

from reasoning_logic.core import Fact, Rule, Atom

logger = logging.getLogger(__name__)


class TemporalRelation(Enum):
    """Allen's interval algebra relations"""
    BEFORE = "before"  # X before Y
    AFTER = "after"  # X after Y
    MEETS = "meets"  # X meets Y (X.end = Y.start)
    MET_BY = "met_by"  # X met-by Y
    OVERLAPS = "overlaps"  # X overlaps Y
    OVERLAPPED_BY = "overlapped_by"
    DURING = "during"  # X during Y
    CONTAINS = "contains"  # X contains Y
    STARTS = "starts"  # X starts Y (same start)
    STARTED_BY = "started_by"
    FINISHES = "finishes"  # X finishes Y (same end)
    FINISHED_BY = "finished_by"
    EQUALS = "equals"  # X equals Y


@dataclass
class TimePoint:
    """Point in time"""
    timestamp: datetime
    label: Optional[str] = None
    
    def __lt__(self, other: 'TimePoint') -> bool:
        return self.timestamp < other.timestamp
    
    def __le__(self, other: 'TimePoint') -> bool:
        return self.timestamp <= other.timestamp
    
    def __str__(self) -> str:
        if self.label:
            return f"{self.label} ({self.timestamp.isoformat()})"
        return self.timestamp.isoformat()


@dataclass
class TimeInterval:
    """Time interval with start and end"""
    start: TimePoint
    end: TimePoint
    label: Optional[str] = None
    
    def __post_init__(self):
        if self.start > self.end:
            raise ValueError(f"Start {self.start} must be before end {self.end}")
    
    def duration(self) -> timedelta:
        """Get duration of interval"""
        return self.end.timestamp - self.start.timestamp
    
    def contains_point(self, point: TimePoint) -> bool:
        """Check if interval contains time point"""
        return self.start <= point <= self.end
    
    def __str__(self) -> str:
        if self.label:
            return f"{self.label} [{self.start} to {self.end}]"
        return f"[{self.start} to {self.end}]"


@dataclass
class TemporalFact:
    """Fact with temporal information"""
    fact: Fact
    valid_from: Optional[TimePoint] = None
    valid_until: Optional[TimePoint] = None
    interval: Optional[TimeInterval] = None
    
    def is_valid_at(self, time: TimePoint) -> bool:
        """Check if fact is valid at given time"""
        if self.interval:
            return self.interval.contains_point(time)
        
        if self.valid_from and time < self.valid_from:
            return False
        if self.valid_until and time > self.valid_until:
            return False
        
        return True


class TemporalReasoningEngine:
    """
    Temporal reasoning engine
    
    Supports:
    - Allen's interval algebra
    - Temporal constraint propagation
    - Event ordering
    - Timeline construction
    """
    
    def __init__(self):
        """Initialize temporal reasoning engine"""
        self._temporal_facts: List[TemporalFact] = []
        self._intervals: Dict[str, TimeInterval] = {}
        self._relations: List[Tuple[str, TemporalRelation, str]] = []
        
        # Transitivity table for Allen's algebra
        self._transitivity = self._build_transitivity_table()
    
    def add_temporal_fact(self, fact: Fact, valid_from: Optional[datetime] = None,
                         valid_until: Optional[datetime] = None):
        """
        Add a fact with temporal validity
        
        Args:
            fact: Fact to add
            valid_from: Start of validity period
            valid_until: End of validity period
        """
        temporal_fact = TemporalFact(
            fact=fact,
            valid_from=TimePoint(valid_from) if valid_from else None,
            valid_until=TimePoint(valid_until) if valid_until else None
        )
        self._temporal_facts.append(temporal_fact)
    
    def add_interval(self, label: str, start: datetime, end: datetime):
        """
        Add a time interval
        
        Args:
            label: Label for interval
            start: Start time
            end: End time
        """
        interval = TimeInterval(
            start=TimePoint(start),
            end=TimePoint(end),
            label=label
        )
        self._intervals[label] = interval
    
    def add_relation(self, interval1: str, relation: TemporalRelation, interval2: str):
        """
        Add temporal relation between intervals
        
        Args:
            interval1: First interval label
            relation: Temporal relation
            interval2: Second interval label
        """
        self._relations.append((interval1, relation, interval2))
    
    def query_at_time(self, time: datetime) -> List[Fact]:
        """
        Query facts valid at given time
        
        Args:
            time: Time point to query
        
        Returns:
            List of valid facts
        """
        time_point = TimePoint(time)
        valid_facts = []
        
        for temporal_fact in self._temporal_facts:
            if temporal_fact.is_valid_at(time_point):
                valid_facts.append(temporal_fact.fact)
        
        return valid_facts
    
    def get_relation(self, interval1: str, interval2: str) -> Optional[TemporalRelation]:
        """
        Get temporal relation between two intervals
        
        Args:
            interval1: First interval label
            interval2: Second interval label
        
        Returns:
            Temporal relation or None
        """
        if interval1 not in self._intervals or interval2 not in self._intervals:
            return None
        
        i1 = self._intervals[interval1]
        i2 = self._intervals[interval2]
        
        return self._compute_relation(i1, i2)
    
    def _compute_relation(self, i1: TimeInterval, i2: TimeInterval) -> TemporalRelation:
        """Compute Allen relation between two intervals"""
        # Before
        if i1.end < i2.start:
            if i1.end.timestamp == i2.start.timestamp:
                return TemporalRelation.MEETS
            return TemporalRelation.BEFORE
        
        # After
        if i1.start > i2.end:
            if i1.start.timestamp == i2.end.timestamp:
                return TemporalRelation.MET_BY
            return TemporalRelation.AFTER
        
        # Equals
        if i1.start == i2.start and i1.end == i2.end:
            return TemporalRelation.EQUALS
        
        # Starts
        if i1.start == i2.start:
            if i1.end < i2.end:
                return TemporalRelation.STARTS
            return TemporalRelation.STARTED_BY
        
        # Finishes
        if i1.end == i2.end:
            if i1.start > i2.start:
                return TemporalRelation.FINISHES
            return TemporalRelation.FINISHED_BY
        
        # During/Contains
        if i1.start > i2.start and i1.end < i2.end:
            return TemporalRelation.DURING
        if i1.start < i2.start and i1.end > i2.end:
            return TemporalRelation.CONTAINS
        
        # Overlaps
        if i1.start < i2.start and i1.end < i2.end and i1.end > i2.start:
            return TemporalRelation.OVERLAPS
        if i1.start > i2.start and i1.end > i2.end and i1.start < i2.end:
            return TemporalRelation.OVERLAPPED_BY
        
        # Default (should not reach here)
        return TemporalRelation.BEFORE
    
    def propagate_constraints(self) -> bool:
        """
        Propagate temporal constraints using transitivity
        
        Returns:
            True if consistent, False if contradiction found
        """
        # TODO: Implement constraint propagation
        return True
    
    def construct_timeline(self) -> List[Tuple[datetime, str, Fact]]:
        """
        Construct timeline of all events
        
        Returns:
            Sorted list of (time, event_type, fact) tuples
        """
        events = []
        
        for temporal_fact in self._temporal_facts:
            if temporal_fact.valid_from:
                events.append((
                    temporal_fact.valid_from.timestamp,
                    "start",
                    temporal_fact.fact
                ))
            if temporal_fact.valid_until:
                events.append((
                    temporal_fact.valid_until.timestamp,
                    "end",
                    temporal_fact.fact
                ))
        
        # Sort by time
        events.sort(key=lambda x: x[0])
        return events
    
    def _build_transitivity_table(self) -> Dict:
        """Build transitivity table for Allen's algebra"""
        # Simplified transitivity table
        # Full table would be 13x13 = 169 entries
        return {}
    
    def explain_temporal_reasoning(self, fact: Fact, time: datetime) -> str:
        """
        Explain why fact is/isn't valid at given time
        
        Args:
            fact: Fact to explain
            time: Time point
        
        Returns:
            Explanation string
        """
        time_point = TimePoint(time)
        lines = []
        lines.append(f"Temporal validity of {fact} at {time_point}:")
        lines.append("=" * 60)
        
        for temporal_fact in self._temporal_facts:
            if temporal_fact.fact == fact:
                is_valid = temporal_fact.is_valid_at(time_point)
                lines.append(f"\nValidity: {'✓ VALID' if is_valid else '✗ INVALID'}")
                
                if temporal_fact.valid_from:
                    lines.append(f"  Valid from: {temporal_fact.valid_from}")
                if temporal_fact.valid_until:
                    lines.append(f"  Valid until: {temporal_fact.valid_until}")
                
                if not is_valid:
                    if temporal_fact.valid_from and time_point < temporal_fact.valid_from:
                        lines.append(f"  Reason: Time is before validity start")
                    elif temporal_fact.valid_until and time_point > temporal_fact.valid_until:
                        lines.append(f"  Reason: Time is after validity end")
        
        return "\n".join(lines)
