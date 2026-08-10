"""Create authentication tables

Revision ID: 001
Revises: 
Create Date: 2026-08-10 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('profile_image', sa.String(length=500), nullable=True),
        sa.Column('bio', sa.String(length=1000), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'], unique=False)

    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)
    op.create_index('ix_roles_id', 'roles', ['id'], unique=False)

    # Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('resource', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_permissions_name', 'permissions', ['name'], unique=True)
    op.create_index('ix_permissions_id', 'permissions', ['id'], unique=False)

    # Create user_roles association table
    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )

    # Create user_permissions association table
    op.create_table(
        'user_permissions',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'permission_id')
    )

    # Create role_permissions association table
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )

    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('access_token', sa.String(length=500), nullable=False),
        sa.Column('refresh_token', sa.String(length=500), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('device_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_activity', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'], unique=False)
    op.create_index('ix_user_sessions_access_token', 'user_sessions', ['access_token'], unique=True)
    op.create_index('ix_user_sessions_refresh_token', 'user_sessions', ['refresh_token'], unique=True)
    op.create_index('ix_user_sessions_is_active', 'user_sessions', ['is_active'], unique=False)
    op.create_index('ix_user_sessions_is_revoked', 'user_sessions', ['is_revoked'], unique=False)
    op.create_index('ix_user_sessions_id', 'user_sessions', ['id'], unique=False)

    # Create login_attempts table
    op.create_table(
        'login_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('failure_reason', sa.String(length=255), nullable=True),
        sa.Column('attempted_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_login_attempts_username', 'login_attempts', ['username'], unique=False)
    op.create_index('ix_login_attempts_success', 'login_attempts', ['success'], unique=False)
    op.create_index('ix_login_attempts_ip_address', 'login_attempts', ['ip_address'], unique=False)
    op.create_index('ix_login_attempts_attempted_at', 'login_attempts', ['attempted_at'], unique=False)
    op.create_index('ix_login_attempts_id', 'login_attempts', ['id'], unique=False)

    # Insert default roles
    op.execute("""
        INSERT INTO roles (name, description) VALUES
        ('ADMIN', 'Full system access with all permissions'),
        ('ANALYST', 'Analysis and reporting access with read/write permissions'),
        ('USER', 'Basic user access with read-only permissions')
    """)

    # Insert default permissions
    op.execute("""
        INSERT INTO permissions (name, resource, description) VALUES
        ('READ', 'verdicts', 'Read verdict data'),
        ('WRITE', 'verdicts', 'Create and update verdict data'),
        ('DELETE', 'verdicts', 'Delete verdict data'),
        ('READ', 'documents', 'Read document data'),
        ('WRITE', 'documents', 'Upload and update documents'),
        ('DELETE', 'documents', 'Delete documents'),
        ('READ', 'models', 'View model information'),
        ('WRITE', 'models', 'Train and update models'),
        ('DELETE', 'models', 'Delete models'),
        ('READ', 'graph', 'Query knowledge graph'),
        ('WRITE', 'graph', 'Modify knowledge graph'),
        ('DELETE', 'graph', 'Delete graph data'),
        ('ADMIN', 'system', 'Full system administration access')
    """)

    # Assign permissions to roles
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'ADMIN'
    """)

    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'ANALYST' AND p.name IN ('READ', 'WRITE')
    """)

    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'USER' AND p.name = 'READ'
    """)


def downgrade() -> None:
    op.drop_index('ix_login_attempts_id', table_name='login_attempts')
    op.drop_index('ix_login_attempts_attempted_at', table_name='login_attempts')
    op.drop_index('ix_login_attempts_ip_address', table_name='login_attempts')
    op.drop_index('ix_login_attempts_success', table_name='login_attempts')
    op.drop_index('ix_login_attempts_username', table_name='login_attempts')
    op.drop_table('login_attempts')
    
    op.drop_index('ix_user_sessions_id', table_name='user_sessions')
    op.drop_index('ix_user_sessions_is_revoked', table_name='user_sessions')
    op.drop_index('ix_user_sessions_is_active', table_name='user_sessions')
    op.drop_index('ix_user_sessions_refresh_token', table_name='user_sessions')
    op.drop_index('ix_user_sessions_access_token', table_name='user_sessions')
    op.drop_index('ix_user_sessions_user_id', table_name='user_sessions')
    op.drop_table('user_sessions')
    
    op.drop_table('role_permissions')
    op.drop_table('user_permissions')
    op.drop_table('user_roles')
    
    op.drop_index('ix_permissions_id', table_name='permissions')
    op.drop_index('ix_permissions_name', table_name='permissions')
    op.drop_table('permissions')
    
    op.drop_index('ix_roles_id', table_name='roles')
    op.drop_index('ix_roles_name', table_name='roles')
    op.drop_table('roles')
    
    op.drop_index('ix_users_id', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
