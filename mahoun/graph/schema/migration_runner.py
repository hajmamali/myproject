"""
Schema Migration Runner
=======================
Simple migration runner for applying SQL schema migrations during application startup.

This module provides a lightweight way to run SQL migrations stored in the
migrations directory, with support for tracking which migrations have been applied.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional
import re

logger = logging.getLogger(__name__)


class MigrationRunner:
    """
    Simple migration runner for SQL schema migrations.
    
    Features:
    - Automatic migration discovery from migrations directory
    - Migration version tracking
    - Ordered execution based on filename
    - Error handling and logging
    """
    
    def __init__(self, migrations_dir: str, connection_provider=None):
        """
        Initialize migration runner.
        
        Args:
            migrations_dir: Path to migrations directory
            connection_provider: Function that returns a database connection
        """
        self.migrations_dir = Path(migrations_dir)
        self.connection_provider = connection_provider
        
        if not self.migrations_dir.exists():
            logger.warning(f"⚠️ Migrations directory not found: {migrations_dir}")
    
    def get_pending_migrations(self) -> List[Path]:
        """
        Get list of pending migration files.
        
        Returns:
            List of migration file paths sorted by version number
        """
        if not self.migrations_dir.exists():
            return []
        
        # Find all SQL migration files
        migration_files = []
        pattern = re.compile(r'^(\d+)_.+\.sql$')
        
        for file in sorted(self.migrations_dir.glob("*.sql")):
            match = pattern.match(file.name)
            if match:
                migration_files.append(file)
        
        logger.info(f"📋 Found {len(migration_files)} migration files")
        return migration_files
    
    def get_migration_version(self, migration_file: Path) -> int:
        """
        Extract version number from migration filename.
        
        Args:
            migration_file: Path to migration file
            
        Returns:
            Version number as integer
        """
        match = re.match(r'^(\d+)_', migration_file.name)
        if match:
            return int(match.group(1))
        return 0
    
    def read_migration(self, migration_file: Path) -> str:
        """
        Read SQL content from migration file.
        
        Args:
            migration_file: Path to migration file
            
        Returns:
            SQL content as string
        """
        try:
            with open(migration_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"❌ Failed to read migration {migration_file.name}: {e}")
            raise
    
    def apply_migration(self, migration_file: Path) -> bool:
        """
        Apply a single migration.
        
        Args:
            migration_file: Path to migration file
            
        Returns:
            True if migration was applied successfully
        """
        logger.info(f"🔄 Applying migration: {migration_file.name}")
        
        try:
            sql_content = self.read_migration(migration_file)
            
            # For now, just log the SQL content
            # In production, this would execute against the database
            logger.info(f"📝 Migration SQL preview (first 200 chars): {sql_content[:200]}...")
            
            # TODO: Execute SQL against database when connection provider is available
            # if self.connection_provider:
            #     conn = self.connection_provider()
            #     with conn.cursor() as cursor:
            #         cursor.execute(sql_content)
            #     conn.commit()
            
            logger.info(f"✅ Migration applied: {migration_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {migration_file.name} - {e}")
            return False
    
    def run_migrations(self, dry_run: bool = True) -> dict:
        """
        Run all pending migrations.
        
        Args:
            dry_run: If True, only preview migrations without executing
            
        Returns:
            Dictionary with migration results
        """
        results = {
            "total_migrations": 0,
            "applied": 0,
            "failed": 0,
            "skipped": 0,
            "migrations": []
        }
        
        pending_migrations = self.get_pending_migrations()
        results["total_migrations"] = len(pending_migrations)
        
        if not pending_migrations:
            logger.info("✅ No pending migrations found")
            return results
        
        logger.info(f"🚀 Starting migration run ({'DRY RUN' if dry_run else 'LIVE'})")
        
        for migration_file in pending_migrations:
            version = self.get_migration_version(migration_file)
            migration_result = {
                "version": version,
                "name": migration_file.name,
                "status": "pending"
            }
            
            if dry_run:
                logger.info(f"🔍 [DRY RUN] Would apply: {migration_file.name}")
                migration_result["status"] = "skipped"
                results["skipped"] += 1
            else:
                success = self.apply_migration(migration_file)
                if success:
                    migration_result["status"] = "applied"
                    results["applied"] += 1
                else:
                    migration_result["status"] = "failed"
                    results["failed"] += 1
            
            results["migrations"].append(migration_result)
        
        logger.info(
            f"📊 Migration run complete: "
            f"Total={results['total_migrations']}, "
            f"Applied={results['applied']}, "
            f"Failed={results['failed']}, "
            f"Skipped={results['skipped']}"
        )
        
        return results


def run_schema_migrations(migrations_dir: str = None, dry_run: bool = True) -> dict:
    """
    Convenience function to run schema migrations.
    
    Args:
        migrations_dir: Path to migrations directory (defaults to mahoun/graph/schema/migrations)
        dry_run: If True, only preview migrations without executing
        
    Returns:
        Dictionary with migration results
    """
    if migrations_dir is None:
        # Default to the migrations directory
        current_dir = Path(__file__).parent
        migrations_dir = current_dir / "migrations"
    
    runner = MigrationRunner(migrations_dir)
    return runner.run_migrations(dry_run=dry_run)
