"""
Data Anonymization for Knowledge Graph
=======================================

Anonymize personal information in the knowledge graph.
"""

import hashlib
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class DataAnonymizer:
    """
    Anonymize personal information in graph data
    
    Features:
    - Hash person names
    - Anonymize phone numbers
    - Anonymize email addresses
    - Anonymize national IDs
    - Preserve data structure for analysis
    """
    
    def __init__(self, salt: str = "mahoun_graph_salt"):
        """
        Initialize anonymizer
        
        Args:
            salt: Salt for hashing (should be kept secret)
        """
        self.salt = salt
        self.anonymized_cache = {}
    
    def hash_name(self, name: str) -> str:
        """
        Hash a person's name
        
        Args:
            name: Person name
        
        Returns:
            Hashed name
        """
        if not name:
            return ""
        
        # Check cache
        if name in self.anonymized_cache:
            return self.anonymized_cache[name]
        
        # Create hash
        hash_input = f"{name}{self.salt}".encode('utf-8')
        hashed = hashlib.sha256(hash_input).hexdigest()[:16]
        
        # Create readable format: PERSON_<hash>
        anonymized = f"PERSON_{hashed}"
        
        # Cache result
        self.anonymized_cache[name] = anonymized
        
        return anonymized
    
    def anonymize_phone(self, phone: str) -> str:
        """
        Anonymize phone number
        
        Args:
            phone: Phone number
        
        Returns:
            Anonymized phone (keeps country code and last 2 digits)
        """
        if not phone:
            return ""
        
        # Remove non-digits
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) < 4:
            return "XXXX"
        
        # Keep first 2 and last 2 digits
        return f"{digits[:2]}{'X' * (len(digits) - 4)}{digits[-2:]}"
    
    def anonymize_email(self, email: str) -> str:
        """
        Anonymize email address
        
        Args:
            email: Email address
        
        Returns:
            Anonymized email
        """
        if not email or '@' not in email:
            return ""
        
        local, domain = email.split('@', 1)
        
        # Keep first and last character of local part
        if len(local) <= 2:
            anonymized_local = 'X' * len(local)
        else:
            anonymized_local = f"{local[0]}{'X' * (len(local) - 2)}{local[-1]}"
        
        return f"{anonymized_local}@{domain}"
    
    def anonymize_national_id(self, national_id: str) -> str:
        """
        Anonymize national ID
        
        Args:
            national_id: National ID number
        
        Returns:
            Anonymized ID (keeps last 3 digits)
        """
        if not national_id:
            return ""
        
        digits = re.sub(r'\D', '', national_id)
        
        if len(digits) < 4:
            return "XXXX"
        
        return f"{'X' * (len(digits) - 3)}{digits[-3:]}"
    
    def anonymize_person_node(self, person_data: Dict) -> Dict:
        """
        Anonymize a Person node
        
        Args:
            person_data: Person node properties
        
        Returns:
            Anonymized person data
        """
        anonymized = person_data.copy()
        
        # Anonymize name
        if 'name' in anonymized:
            anonymized['name'] = self.hash_name(anonymized['name'])
            anonymized['original_name_hash'] = True
        
        # Anonymize phone
        if 'phone' in anonymized:
            anonymized['phone'] = self.anonymize_phone(anonymized['phone'])
        
        # Anonymize email
        if 'email' in anonymized:
            anonymized['email'] = self.anonymize_email(anonymized['email'])
        
        # Anonymize national ID
        if 'national_id' in anonymized:
            anonymized['national_id'] = self.anonymize_national_id(
                anonymized['national_id']
            )
        
        # Add anonymization metadata
        anonymized['anonymized'] = True
        anonymized['anonymized_at'] = datetime.now().isoformat()
        
        return anonymized
    
    def anonymize_graph_data(
        self,
        connection,
        node_types: Optional[List[str]] = None
    ) -> Dict:
        """
        Anonymize personal data in the graph
        
        Args:
            connection: Neo4j connection
            node_types: Node types to anonymize (default: ['Person'])
        
        Returns:
            Anonymization statistics
        """
        if node_types is None:
            node_types = ['Person']
        
        logger.info(f"Starting anonymization for node types: {node_types}")
        
        stats = {
            'total_anonymized': 0,
            'by_type': {},
            'start_time': datetime.now().isoformat()
        }
        
        try:
            for node_type in node_types:
                logger.info(f"Anonymizing {node_type} nodes...")
                
                # Get all nodes of this type
                query = f"""
                MATCH (n:{node_type})
                WHERE n.anonymized IS NULL OR n.anonymized = false
                RETURN n
                LIMIT 1000
                """
                
                batch_count = 0
                total_count = 0
                
                while True:
                    results = connection.execute_query(query)
                    
                    if not results:
                        break
                    
                    batch_count = len(results)
                    total_count += batch_count
                    
                    # Anonymize each node
                    for row in results:
                        node = row['n']
                        node_id = node.get('id')
                        
                        # Anonymize data
                        anonymized = self.anonymize_person_node(dict(node))
                        
                        # Update node in graph
                        update_query = f"""
                        MATCH (n:{node_type} {{id: $id}})
                        SET n += $properties
                        """
                        
                        connection.execute_query(
                            update_query,
                            {'id': node_id, 'properties': anonymized}
                        )
                    
                    logger.info(f"Anonymized {batch_count} {node_type} nodes")
                    
                    if batch_count < 1000:
                        break
                
                stats['by_type'][node_type] = total_count
                stats['total_anonymized'] += total_count
                
                logger.info(f"Completed {node_type}: {total_count} nodes anonymized")
            
            stats['end_time'] = datetime.now().isoformat()
            stats['status'] = 'completed'
            
            logger.info(
                f"Anonymization complete: {stats['total_anonymized']} nodes"
            )
            
            return stats
        
        except Exception as e:
            logger.error(f"Anonymization failed: {e}", exc_info=True)
            stats['status'] = 'failed'
            stats['error'] = str(e)
            return stats
    
    def verify_anonymization(self, connection) -> Dict:
        """
        Verify that personal data has been anonymized
        
        Args:
            connection: Neo4j connection
        
        Returns:
            Verification report
        """
        logger.info("Verifying anonymization...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'issues': []
        }
        
        try:
            # Check 1: All Person nodes should be anonymized
            query1 = """
            MATCH (p:Person)
            WHERE p.anonymized IS NULL OR p.anonymized = false
            RETURN count(p) as count
            """
            
            result = connection.execute_query(query1)
            unanonymized_count = result[0]['count'] if result else 0
            
            report['checks']['unanonymized_persons'] = unanonymized_count
            
            if unanonymized_count > 0:
                report['issues'].append(
                    f"{unanonymized_count} Person nodes not anonymized"
                )
            
            # Check 2: No plain email addresses
            query2 = """
            MATCH (n)
            WHERE n.email =~ '.*@.*\\.[a-z]{2,}'
            AND (n.anonymized IS NULL OR n.anonymized = false)
            RETURN count(n) as count
            """
            
            result = connection.execute_query(query2)
            plain_emails = result[0]['count'] if result else 0
            
            report['checks']['plain_emails'] = plain_emails
            
            if plain_emails > 0:
                report['issues'].append(
                    f"{plain_emails} nodes with plain email addresses"
                )
            
            # Determine status
            report['status'] = 'passed' if len(report['issues']) == 0 else 'failed'
            
            logger.info(f"Verification {report['status']}: {len(report['issues'])} issues")
            
            return report
        
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            report['status'] = 'error'
            report['error'] = str(e)
            return report


# ============================================================================
# Convenience Functions
# ============================================================================

def anonymize_graph(connection, salt: str = "mahoun_graph_salt") -> Dict:
    """
    Quick anonymization function
    
    Args:
        connection: Neo4j connection
        salt: Salt for hashing
    
    Returns:
        Anonymization statistics
    """
    anonymizer = DataAnonymizer(salt)
    return anonymizer.anonymize_graph_data(connection)


def verify_anonymization(connection) -> Dict:
    """
    Quick verification function
    
    Args:
        connection: Neo4j connection
    
    Returns:
        Verification report
    """
    anonymizer = DataAnonymizer()
    return anonymizer.verify_anonymization(connection)
