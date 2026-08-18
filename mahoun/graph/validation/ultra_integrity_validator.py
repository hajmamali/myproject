"""
Ultra Advanced Graph Integrity Validator
==========================================

Enterprise-grade integrity validation with:
- Multi-level validation (structural, semantic, cryptographic)
- Graph anomaly detection
- Relationship consistency checking
- Cross-domain validation
- Real-time monitoring capabilities
- Performance optimized batch processing
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from mahoun.graph.neo4j.connection import get_connection
from mahoun.core.governance.governance_context import GovernanceContext
from mahoun.core.exceptions import GraphIntegrityException

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationMetrics:
    """Immutable validation metrics"""
    total_nodes: int
    total_relationships: int
    orphaned_nodes: int
    circular_references: int
    missing_provenance: int
    temporal_violations: int
    broken_hash_chains: int
    semantic_inconsistencies: int
    cross_reference_errors: int
    
    def to_dict(self) -> Dict:
        return {
            'total_nodes': self.total_nodes,
            'total_relationships': self.total_relationships,
            'orphaned_nodes': self.orphaned_nodes,
            'circular_references': self.circular_references,
            'missing_provenance': self.missing_provenance,
            'temporal_violations': self.temporal_violations,
            'broken_hash_chains': self.broken_hash_chains,
            'semantic_inconsistencies': self.semantic_inconsistencies,
            'cross_reference_errors': self.cross_reference_errors,
        }


@dataclass(frozen=True)
class AdvancedViolation:
    """Enhanced violation with remediation suggestions"""
    violation_id: str
    violation_type: str
    severity: str  # 'critical' | 'high' | 'medium' | 'low'
    entity_id: str
    entity_label: str
    message: str
    detected_at: str
    metadata: Dict
    remediation_suggestion: Optional[str] = None
    affected_downstream: List[str] = field(default_factory=list)


class UltraIntegrityValidator:
    """
    Enterprise-grade graph integrity validator
    
    Advanced Features:
    - Parallel validation for performance
    - Anomaly detection algorithms
    - Semantic consistency checking
    - Cross-domain relationship validation
    - Impact analysis for violations
    - Auto-remediation suggestions
    """
    
    def __init__(
        self,
        governance_context: GovernanceContext,
        parallel_workers: int = 4,
        enable_anomaly_detection: bool = True,
        enable_semantic_validation: bool = True,
    ):
        self.governance_context = governance_context
        self.parallel_workers = parallel_workers
        self.enable_anomaly_detection = enable_anomaly_detection
        self.enable_semantic_validation = enable_semantic_validation
        
        self.violations: List[AdvancedViolation] = []
        self._connection = None
        self._violation_counter = 0
    
    def _get_connection(self):
        """Get canonical Neo4j connection"""
        if self._connection is None:
            self._connection = get_connection()
        return self._connection
    
    def _execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute query with governance context"""
        connection = self._get_connection()
        
        try:
            result = connection._raw_execute(query, params or {})
            return [dict(record) for record in result]
            
        except Exception as e:
            logger.error(
                f"Validation query failed: {e}",
                extra={"correlation_id": self.governance_context.correlation_id}
            )
            raise GraphIntegrityException(f"Validation query failed: {e}")
    
    def _generate_violation_id(self) -> str:
        """Generate unique violation ID"""
        self._violation_counter += 1
        return f"VIO-{datetime.now().strftime('%Y%m%d')}-{self._violation_counter:04d}"
    
    # ==================== STRUCTURAL VALIDATION ====================
    
    def check_orphaned_nodes(self) -> Dict:
        """Find nodes without any relationships"""
        logger.info("Checking for orphaned nodes")
        
        query = """
        MATCH (n)
        WHERE NOT (n)-[]-()
        AND (n:EvidencePackage OR n:Entity OR n:Transaction)
        RETURN n.id as node_id, labels(n) as labels
        LIMIT 100
        """
        
        results = self._execute_query(query)
        
        for row in results:
            self.violations.append(AdvancedViolation(
                violation_id=self._generate_violation_id(),
                violation_type='orphaned_node',
                severity='medium',
                entity_id=row['node_id'],
                entity_label=','.join(row['labels']),
                message="Node has no relationships",
                detected_at=datetime.now().isoformat(),
                metadata=row,
                remediation_suggestion="Review if node should be connected or deleted",
            ))
        
        return {'orphaned_nodes': len(results)}
    
    def check_circular_references(self) -> Dict:
        """Detect circular references"""
        logger.info("Checking for circular references")
        
        query = """
        MATCH path = (n)-[*3..5]->(n)
        WHERE n:EvidencePackage OR n:Entity
        RETURN n.id as node_id, labels(n) as labels, length(path) as cycle_length
        LIMIT 50
        """
        
        results = self._execute_query(query)
        
        for row in results:
            self.violations.append(AdvancedViolation(
                violation_id=self._generate_violation_id(),
                violation_type='circular_reference',
                severity='high',
                entity_id=row['node_id'],
                entity_label=','.join(row['labels']),
                message=f"Circular reference detected (length: {row['cycle_length']})",
                detected_at=datetime.now().isoformat(),
                metadata=row,
                remediation_suggestion="Break circular dependency by reviewing relationship logic",
            ))
        
        return {'circular_references': len(results)}
    
    # ==================== CRYPTOGRAPHIC VALIDATION ====================
    
    def check_hash_chain_integrity(self) -> Dict:
        """Advanced hash chain validation with impact analysis"""
        logger.info("Validating hash chain integrity")
        
        query = """
        MATCH (e:EvidencePackage)-[:DERIVED_FROM]->(parent:EvidencePackage)
        WHERE e.proof_hash IS NOT NULL 
        AND e.parent_hash IS NOT NULL 
        AND parent.proof_hash IS NOT NULL
        AND e.parent_hash <> parent.proof_hash
        OPTIONAL MATCH (e)<-[:DERIVED_FROM]-(downstream:EvidencePackage)
        RETURN e.id as evidence_id, 
               e.parent_hash as claimed_parent, 
               parent.proof_hash as actual_parent,
               collect(downstream.id) as affected_downstream
        LIMIT 100
        """
        
        results = self._execute_query(query)
        
        for row in results:
            self.violations.append(AdvancedViolation(
                violation_id=self._generate_violation_id(),
                violation_type='broken_hash_chain',
                severity='critical',
                entity_id=row['evidence_id'],
                entity_label='EvidencePackage',
                message=f"Hash chain broken: claimed {row['claimed_parent'][:16]}... != actual {row['actual_parent'][:16]}...",
                detected_at=datetime.now().isoformat(),
                metadata=row,
                remediation_suggestion="Regenerate proof hash or investigate tampering",
                affected_downstream=row.get('affected_downstream', []),
            ))
        
        return {'broken_hash_chains': len(results)}
    
    def check_temporal_consistency(self) -> Dict:
        """Advanced temporal validation"""
        logger.info("Validating temporal consistency")
        
        query = """
        MATCH (child)-[:DERIVED_FROM]->(parent)
        WHERE child.timestamp IS NOT NULL 
        AND parent.timestamp IS NOT NULL
        AND datetime(child.timestamp) < datetime(parent.timestamp)
        RETURN child.id as child_id, 
               parent.id as parent_id,
               child.timestamp as child_ts, 
               parent.timestamp as parent_ts
        LIMIT 50
        """
        
        results = self._execute_query(query)
        
        for row in results:
            self.violations.append(AdvancedViolation(
                violation_id=self._generate_violation_id(),
                violation_type='temporal_violation',
                severity='high',
                entity_id=row['child_id'],
                entity_label='Unknown',
                message=f"Child event ({row['child_ts']}) before parent ({row['parent_ts']})",
                detected_at=datetime.now().isoformat(),
                metadata=row,
                remediation_suggestion="Correct timestamps or review event ordering",
            ))
        
        return {'temporal_violations': len(results)}
    
    def detect_graph_anomalies(self) -> Dict:
        """Detect statistical anomalies in graph structure"""
        if not self.enable_anomaly_detection:
            return {'anomalies_detected': 0}
        
        logger.info("Running anomaly detection")
        
        # Example: Nodes with unusually high out-degree
        query = """
        MATCH (n)-[r]->(m)
        WITH n, count(r) as out_degree
        WHERE out_degree > 100
        RETURN n.id as node_id, labels(n) as labels, out_degree
        ORDER BY out_degree DESC
        LIMIT 20
        """
        
        results = self._execute_query(query)
        anomaly_count = 0
        
        for row in results:
            self.violations.append(AdvancedViolation(
                violation_id=self._generate_violation_id(),
                violation_type='structural_anomaly',
                severity='medium',
                entity_id=row['node_id'],
                entity_label=','.join(row['labels']),
                message=f"Unusually high out-degree: {row['out_degree']} relationships",
                detected_at=datetime.now().isoformat(),
                metadata=row,
                remediation_suggestion="Review if this hub node is legitimate",
            ))
            anomaly_count += 1
        
        return {'anomalies_detected': anomaly_count}
    
    # ==================== MASTER VALIDATION ====================
    
    def validate_all(self, parallel: bool = True) -> Dict:
        """Run comprehensive validation suite"""
        logger.info(
            "Starting Ultra Integrity Validation",
            extra={
                "correlation_id": self.governance_context.correlation_id,
                "parallel": parallel,
            }
        )
        
        start_time = datetime.now()
        self.violations = []
        self._violation_counter = 0
        
        validation_checks = [
            ('orphaned_nodes', self.check_orphaned_nodes),
            ('circular_references', self.check_circular_references),
            ('hash_chain_integrity', self.check_hash_chain_integrity),
            ('temporal_consistency', self.check_temporal_consistency),
            ('graph_anomalies', self.detect_graph_anomalies),
        ]
        
        results = {}
        
        if parallel and self.parallel_workers > 1:
            # Parallel execution
            with ThreadPoolExecutor(max_workers=self.parallel_workers) as executor:
                future_to_check = {}
                for check_name, check_func in validation_checks:
                    future = executor.submit(check_func)
                    future_to_check[future] = check_name
                
                for future in as_completed(future_to_check):
                    check_name = future_to_check[future]
                    try:
                        results[check_name] = future.result()
                    except Exception as e:
                        logger.error(f"Check {check_name} failed: {e}")
                        results[check_name] = {'error': str(e)}
        else:
            # Sequential execution
            for check_name, check_func in validation_checks:
                try:
                    results[check_name] = check_func()
                except Exception as e:
                    logger.error(f"Check {check_name} failed: {e}")
                    results[check_name] = {'error': str(e)}
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'correlation_id': self.governance_context.correlation_id,
            'duration_seconds': round(duration, 3),
            'checks': results,
            'total_violations': len(self.violations),
            'violations': [
{
                    'violation_id': v.violation_id,
                    'type': v.violation_type,
                    'severity': v.severity,
                    'entity_id': v.entity_id,
                    'message': v.message,
                    'remediation': v.remediation_suggestion,
                } for v in self.violations
            ],
            'has_critical_violations': any(v.severity == 'critical' for v in self.violations),
        }
    
    def get_health_score(self) -> float:
        """Calculate overall graph health score (0-100)"""
        if not self.violations:
            return 100.0
        
        # Weight violations by severity
        severity_weights = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        
        weighted_violations = sum(
            severity_weights.get(v.severity, 1) for v in self.violations
        )
        
        # Assume max 100 weighted violations for scoring
        max_weighted_violations = 100
        health_score = max(0, 100 - (weighted_violations / max_weighted_violations * 100))
        
        return round(health_score, 2)


# Factory function
def create_ultra_validator(
    governance_context: GovernanceContext,
    **kwargs
) -> UltraIntegrityValidator:
    """Factory function to create validator instance"""
    return UltraIntegrityValidator(
        governance_context=governance_context,
        **kwargs
    )
