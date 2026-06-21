"""Unit Tests for DevOps Essentials Edge Cases"""
import os
import sys
import tarfile
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.backup import backup_ledger, backup_neo4j
from scripts.restore import detect_archive_type, verify_archive_integrity, restore_ledger, restore_neo4j


def test_backup_missing_ledger_directory():
    """Test missing ledger directory error (Requirement 1.3)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        backup_dir = tmpdir_path / "backups"
        backup_dir.mkdir()
        
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            with pytest.raises(FileNotFoundError) as exc_info:
                backup_ledger(backup_dir, dry_run=False)
            assert "Ledger directory not found" in str(exc_info.value)
        finally:
            os.chdir(original_cwd)


def test_restore_corrupted_archive():
    """Test restore with corrupted tar.gz file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        corrupted_archive = Path(tmpdir) / "ledger_backup_20250101_120000.tar.gz"
        corrupted_archive.write_bytes(b"Not a valid tar.gz")
        with pytest.raises(tarfile.ReadError):
            verify_archive_integrity(corrupted_archive)


def test_detect_archive_type_ledger():
    """Test archive type detection for ledger"""
    archive_path = Path("ledger_backup_20250214_143022.tar.gz")
    assert detect_archive_type(archive_path) == "ledger"


def test_detect_archive_type_neo4j():
    """Test archive type detection for neo4j"""
    archive_path = Path("neo4j_backup_20250214_143022.dump")
    assert detect_archive_type(archive_path) == "neo4j"
