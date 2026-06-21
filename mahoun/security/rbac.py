"""
Role-Based Access Control (RBAC) for Knowledge Graph
=====================================================

Manage user roles and permissions for graph access.
"""

import logging
from typing import Dict, List, Optional, Set
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles"""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    API_USER = "api_user"


class Permission(str, Enum):
    """Graph permissions"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXPORT = "export"
    ANONYMIZE = "anonymize"


# Role-Permission mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: {
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.ADMIN,
        Permission.EXPORT,
        Permission.ANONYMIZE,
    },
    Role.ANALYST: {
        Permission.READ,
        Permission.WRITE,
        Permission.EXPORT,
    },
    Role.VIEWER: {
        Permission.READ,
    },
    Role.API_USER: {
        Permission.READ,
        Permission.WRITE,
    },
}


class RBACManager:
    """
    Role-Based Access Control manager
    
    Features:
    - User role management
    - Permission checking
    - Audit logging
    - Neo4j authentication integration
    """
    
    def __init__(self, connection=None):
        """
        Initialize RBAC manager
        
        Args:
            connection: Neo4j connection (optional)
        """
        self.connection = connection
        self.users = {}  # In-memory user store (use DB in production)
        self.audit_log = []
    
    def create_user(
        self,
        username: str,
        role: Role,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create a new user
        
        Args:
            username: Username
            role: User role
            metadata: Additional user metadata
        
        Returns:
            User information
        """
        if username in self.users:
            raise ValueError(f"User already exists: {username}")
        
        user = {
            'username': username,
            'role': role,
            'permissions': list(ROLE_PERMISSIONS[role]),
            'created_at': datetime.now().isoformat(),
            'metadata': metadata or {},
        }
        
        self.users[username] = user
        
        self._audit_log(
            action='create_user',
            username=username,
            details={'role': role}
        )
        
        logger.info(f"Created user: {username} (role={role})")
        
        return user
    
    def get_user(self, username: str) -> Optional[Dict]:
        """
        Get user information
        
        Args:
            username: Username
        
        Returns:
            User information or None
        """
        return self.users.get(username)
    
    def update_user_role(self, username: str, new_role: Role) -> bool:
        """
        Update user role
        
        Args:
            username: Username
            new_role: New role
        
        Returns:
            True if successful
        """
        if username not in self.users:
            logger.error(f"User not found: {username}")
            return False
        
        old_role = self.users[username]['role']
        self.users[username]['role'] = new_role
        self.users[username]['permissions'] = list(ROLE_PERMISSIONS[new_role])
        
        self._audit_log(
            action='update_role',
            username=username,
            details={'old_role': old_role, 'new_role': new_role}
        )
        
        logger.info(f"Updated user role: {username} ({old_role} -> {new_role})")
        
        return True
    
    def delete_user(self, username: str) -> bool:
        """
        Delete a user
        
        Args:
            username: Username
        
        Returns:
            True if successful
        """
        if username not in self.users:
            logger.error(f"User not found: {username}")
            return False
        
        del self.users[username]
        
        self._audit_log(
            action='delete_user',
            username=username
        )
        
        logger.info(f"Deleted user: {username}")
        
        return True
    
    def check_permission(
        self,
        username: str,
        permission: Permission
    ) -> bool:
        """
        Check if user has permission
        
        Args:
            username: Username
            permission: Required permission
        
        Returns:
            True if user has permission
        """
        user = self.get_user(username)
        
        if not user:
            logger.warning(f"Permission check failed: user not found ({username})")
            return False
        
        has_permission = permission in user['permissions']
        
        if not has_permission:
            logger.warning(
                f"Permission denied: {username} does not have {permission}"
            )
        
        return has_permission
    
    def require_permission(
        self,
        username: str,
        permission: Permission
    ):
        """
        Require permission (raises exception if not authorized)
        
        Args:
            username: Username
            permission: Required permission
        
        Raises:
            PermissionError: If user doesn't have permission
        """
        if not self.check_permission(username, permission):
            raise PermissionError(
                f"User {username} does not have {permission} permission"
            )
    
    def list_users(self) -> List[Dict]:
        """
        List all users
        
        Returns:
            List of user information
        """
        return list(self.users.values())
    
    def get_audit_log(
        self,
        username: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get audit log
        
        Args:
            username: Filter by username (optional)
            limit: Maximum number of entries
        
        Returns:
            Audit log entries
        """
        logs = self.audit_log
        
        if username:
            logs = [log for log in logs if log['username'] == username]
        
        return logs[-limit:]
    
    def _audit_log(
        self,
        action: str,
        username: str,
        details: Optional[Dict] = None
    ):
        """
        Add entry to audit log
        
        Args:
            action: Action performed
            username: Username
            details: Additional details
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'username': username,
            'details': details or {},
        }
        
        self.audit_log.append(entry)
        
        # Keep only last 10000 entries
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-10000:]
    
    def setup_neo4j_auth(
        self,
        username: str,
        password: str,
        role: Role
    ) -> bool:
        """
        Setup Neo4j authentication for user
        
        Args:
            username: Neo4j username
            password: Neo4j password
            role: User role
        
        Returns:
            True if successful
        """
        if not self.connection:
            logger.error("No Neo4j connection available")
            return False
        
        try:
            # Map role to Neo4j role
            neo4j_role = self._map_role_to_neo4j(role)
            
            # Create user in Neo4j
            create_query = f"""
            CREATE USER {username}
            SET PASSWORD '{password}'
            SET PASSWORD CHANGE NOT REQUIRED
            """
            
            self.connection.execute_query(create_query)
            
            # Grant role
            grant_query = f"""
            GRANT ROLE {neo4j_role} TO {username}
            """
            
            self.connection.execute_query(grant_query)
            
            logger.info(f"Created Neo4j user: {username} (role={neo4j_role})")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to setup Neo4j auth: {e}")
            return False
    
    def _map_role_to_neo4j(self, role: Role) -> str:
        """Map application role to Neo4j role"""
        mapping = {
            Role.ADMIN: 'admin',
            Role.ANALYST: 'editor',
            Role.VIEWER: 'reader',
            Role.API_USER: 'editor',
        }
        return mapping.get(role, 'reader')


# ============================================================================
# Decorator for permission checking
# ============================================================================

def require_permission(permission: Permission):
    """
    Decorator to require permission for a function
    
    Usage:
        @require_permission(Permission.WRITE)
        def update_graph(username, data):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get username from kwargs or first arg
            username = kwargs.get('username') or (args[0] if args else None)
            
            if not username:
                raise ValueError("Username required for permission check")
            
            # Check permission
            rbac = RBACManager()
            rbac.require_permission(username, permission)
            
            # Call function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# Convenience Functions
# ============================================================================

def create_default_users(rbac: RBACManager):
    """
    Create default users for testing
    
    Args:
        rbac: RBAC manager
    """
    # Admin user
    rbac.create_user(
        username='admin',
        role=Role.ADMIN,
        metadata={'description': 'System administrator'}
    )
    
    # Analyst user
    rbac.create_user(
        username='analyst',
        role=Role.ANALYST,
        metadata={'description': 'Data analyst'}
    )
    
    # Viewer user
    rbac.create_user(
        username='viewer',
        role=Role.VIEWER,
        metadata={'description': 'Read-only user'}
    )
    
    logger.info("Created default users")
