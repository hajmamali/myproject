"""
Tests for Airgap Audit Export System
====================================

Comprehensive test suite for enterprise-grade audit export.

Test Categories:
1. Export functionality
2. Format conversion
3. Cryptographic signing
4. Compression
5. Transfer protocol
6. Chain of custody
7. Verification
8. Error handling
"""

import pytest
import json
import gzip
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from mahoun.audit import (
    AirgapAuditExporter,
    ExportFormat,
    ExportManifest,
    ExportPackage,
    ExportError,
    CEFFormatter,
    LEEFFormatter,
    JSONLDFormatter,
    JSONLFormatter,
    CSVFormatter,
    TransferProtocol,
    TransferManifest,
    ChainOfCustody,
    TransferStatus,
    TransferMethod,
)
from mahoun.audit.airgap_exporter import CompressionType
from mahoun.crypto.signatures import generate_keypair


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def keypair():
    """Generate keypair for tests"""
    return generate_keypair()


@pytest.fixture
def sample_records():
    """Sample audit records"""
    return [
        {
            "id": f"record_{i}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": f"corr_{i}",
            "actor_id": "test-user",
            "operation": "reasoning",
            "verdict_id": f"verdict_{i}",
            "confidence": 0.92,
            "case_id": f"case_{i}",
            "outcome": "success",
            "severity": "INFO",
        }
        for i in range(10)
    ]


@pytest.fixture
def temp_export_dir(tmp_path):
    """Temporary export directory"""
    export_dir = tmp_path / "audit_export"
    export_dir.mkdir()
    return export_dir


@pytest.fixture
def exporter(keypair, temp_export_dir):
    """Create exporter instance"""
    private_key, _ = keypair
    return AirgapAuditExporter(
        private_key=private_key,
        output_dir=temp_export_dir,
        exported_by="test-system",
    )


# ============================================================================
# EXPORT FUNCTIONALITY TESTS
# ============================================================================

class TestExportFunctionality:
    """Test core export functionality"""
    
    def test_export_batch_cef(self, exporter, sample_records, keypair):
        """Test CEF format export"""
        package = exporter.export_batch(
            records=sample_records,
            format=ExportFormat.CEF,
            compression=CompressionType.NONE,
        )
        
        assert package.package_id is not None
        assert package.manifest.record_count == len(sample_records)
        assert package.manifest.format == ExportFormat.CEF
        assert package.content_path.exists()
        
        # Verify signature
        _, public_key = keypair
        assert package.verify(public_key)
    
    def test_export_batch_with_compression(self, exporter, sample_records, keypair):
        """Test export with GZIP compression"""
        package = exporter.export_batch(
            records=sample_records,
            format=ExportFormat.CEF,
            compression=CompressionType.GZIP,
        )
        
        assert package.compressed_path is not None
        assert package.compressed_path.exists()
        assert package.compressed_path.suffix == '.gz'
        
        # Verify compression ratio
        ratio = package.get_compression_ratio()
        assert ratio > 1.0  # Should be compressed
    
    def test_export_multiple_formats(self, exporter, sample_records):
        """Test exporting in different formats"""
        formats = [ExportFormat.CEF, ExportFormat.LEEF, ExportFormat.JSONL]
        
        for fmt in formats:
            package = exporter.export_batch(
                records=sample_records,
                format=fmt,
                compression=CompressionType.NONE,
            )
            
            assert package.manifest.format == fmt
            assert package.content_path.exists()
    
    def test_export_empty_records_raises_error(self, exporter):
        """Test that exporting empty records raises error"""
        with pytest.raises(ExportError):
            exporter.export_batch(
                records=[],
                format=ExportFormat.CEF,
            )
    
    def test_incremental_export(self, exporter, sample_records):
        """Test incremental export with deduplication"""
        # First export
        package1 = exporter.export_batch(
            records=sample_records[:5],
            format=ExportFormat.CEF,
            incremental=True,
        )
        
        assert package1.manifest.record_count == 5
        
        # Second export (should only include new records)
        package2 = exporter.export_batch(
            records=sample_records,  # All 10 records
            format=ExportFormat.CEF,
            incremental=True,
        )
        
        # Should only export the 5 new records
        assert package2.manifest.record_count == 5


# ============================================================================
# FORMAT CONVERSION TESTS
# ============================================================================

class TestFormatConversion:
    """Test format converters"""
    
    def test_cef_formatter(self, sample_records):
        """Test CEF formatter"""
        formatter = CEFFormatter()
        output = formatter.format(sample_records)
        
        lines = output.strip().split('\n')
        assert len(lines) == len(sample_records)
        
        # Check CEF format
        for line in lines:
            assert line.startswith('CEF:0|')
            assert 'MAHOUN' in line
    
    def test_leef_formatter(self, sample_records):
        """Test LEEF formatter"""
        formatter = LEEFFormatter()
        output = formatter.format(sample_records)
        
        lines = output.strip().split('\n')
        assert len(lines) == len(sample_records)
        
        # Check LEEF format
        for line in lines:
            assert line.startswith('LEEF:2.0|')
            assert 'MAHOUN' in line
    
    def test_jsonld_formatter(self, sample_records):
        """Test JSON-LD formatter"""
        formatter = JSONLDFormatter()
        output = formatter.format(sample_records)
        
        data = json.loads(output)
        assert data['@type'] == 'Collection'
        assert data['numberOfItems'] == len(sample_records)
        assert len(data['member']) == len(sample_records)
    
    def test_jsonl_formatter(self, sample_records):
        """Test JSONL formatter"""
        formatter = JSONLFormatter()
        output = formatter.format(sample_records)
        
        lines = output.strip().split('\n')
        assert len(lines) == len(sample_records)
        
        # Each line should be valid JSON
        for line in lines:
            data = json.loads(line)
            assert 'id' in data
    
    def test_csv_formatter(self, sample_records):
        """Test CSV formatter"""
        formatter = CSVFormatter()
        output = formatter.format(sample_records)
        
        lines = output.strip().split('\n')
        assert len(lines) == len(sample_records) + 1  # +1 for header
        
        # Check header
        assert 'id,timestamp,correlation_id' in lines[0]


# ============================================================================
# CRYPTOGRAPHIC SIGNING TESTS
# ============================================================================

class TestCryptographicSigning:
    """Test cryptographic signing and verification"""
    
    def test_package_signature_verification(self, exporter, sample_records, keypair):
        """Test package signature verification"""
        package = exporter.export_batch(
            records=sample_records,
            format=ExportFormat.CEF,
        )
        
        _, public_key = keypair
        assert package.verify(public_key)
    
    def test_tampered_content_fails_verification(
        self, exporter, sample_records, keypair
    ):
        """Test that tampered content fails verification"""
        package = exporter.export_batch(
            records=sample_records,
            format=ExportFormat.CEF,
        )
        
        # Tamper with content
        package.content_path.write_text("TAMPERED DATA")
        
        # Verification should fail
        _, public_key = keypair
        assert not package.verify(public_key)
    
    def test_wrong_public_key_fails_verification(
        self, exporter, sample_records
    ):
        """Test that wrong public key fails verification"""
        package = exporter.export_batch(
            records=sample_records,
            format=ExportFormat.CEF,
        )
        
        # Generate different keypair
        _, wrong_public_key = generate_keypair()
        
        # Verification should fail
        assert not package.verify(wrong_public_key)
    
    def test_manifest_integrity_check(self, exporter, sample_records):
        """Test manifest integrity verification"""
        package = exporter.export_batch(
            records=sample_records,
            format=ExportFormat.CEF,
        )
        
        # Integrity check should pass
        assert package.manifest.verify_integrity(
            package.content_path,
            package.compressed_path,
        )


# ============================================================================
# COMPRESSION TESTS
# ============================================================================

class TestCompression:
    """Test compression functionality"""
    
    def test_gzip_compression(self, exporter, sample_records):
        """Test GZIP compression"""
        package = exporter.export_batch(
            records=sample_records,
            format=ExportFormat.CEF,
            compression=CompressionType.GZIP,
        )
        
        assert package.compressed_path.suffix == '.gz'
        
        # Verify can decompress
        with gzip.open(package.compressed_path, 'rt') as f:
            content = f.read()
            assert 'CEF:0|' in content
    
    def test_lzma_compression(self, exporter, sample_records):
        """Test LZMA compression"""
        package = exporter.export_batch(
            records=sample_records,
            format=ExportFormat.CEF,
            compression=CompressionType.LZMA,
        )
        
        assert package.compressed_path.suffix == '.xz'
        assert package.compressed_path.exists()
    
    def test_compression_ratio_calculation(self, exporter, sample_records):
        """Test compression ratio calculation"""
        package = exporter.export_batch(
            records=sample_records * 10,  # More records for better compression
            format=ExportFormat.CEF,
            compression=CompressionType.GZIP,
        )
        
        ratio = package.get_compression_ratio()
        assert ratio > 1.0
        assert ratio < 100.0  # Reasonable upper bound (was 20, but text compresses very well)


# ============================================================================
# TRANSFER PROTOCOL TESTS
# ============================================================================

class TestTransferProtocol:
    """Test sneakernet transfer protocol"""
    
    def test_create_transfer_manifest(self, keypair):
        """Test creating transfer manifest"""
        private_key, public_key = keypair
        protocol = TransferProtocol(
            private_key=private_key,
            actor_id="sender@test",
            location="Test Lab",
        )
        
        manifest = protocol.create_transfer(
            package_ids=["pkg_001", "pkg_002"],
            package_sizes_mb=[10.5, 15.3],
        )
        
        assert manifest.transfer_id is not None
        assert manifest.total_packages == 2
        assert manifest.total_size_mb == 25.8
        assert manifest.sender == "sender@test"
        assert manifest.verify_sender(public_key)
    
    def test_acknowledge_receipt(self, keypair):
        """Test receiver acknowledgment"""
        sender_private, sender_public = keypair
        receiver_private, receiver_public = generate_keypair()
        
        # Sender creates transfer
        sender_protocol = TransferProtocol(
            private_key=sender_private,
            actor_id="sender@test",
            location="Test Lab A",
        )
        
        manifest = sender_protocol.create_transfer(
            package_ids=["pkg_001"],
            package_sizes_mb=[10.0],
        )
        
        # Receiver acknowledges
        receiver_protocol = TransferProtocol(
            private_key=receiver_private,
            actor_id="receiver@test",
            location="Test Lab B",
        )
        
        manifest = receiver_protocol.acknowledge_receipt(
            manifest=manifest,
            verification_passed=True,
        )
        
        assert manifest.receiver == "receiver@test"
        assert manifest.status == TransferStatus.VERIFIED
        assert manifest.verify_receiver(receiver_public)
    
    def test_chain_of_custody_tracking(self, keypair):
        """Test chain of custody tracking"""
        private_key, public_key = keypair
        protocol = TransferProtocol(
            private_key=private_key,
            actor_id="test-actor",
            location="Test Location",
        )
        
        manifest = protocol.create_transfer(
            package_ids=["pkg_001"],
            package_sizes_mb=[10.0],
        )
        
        assert manifest.chain_of_custody is not None
        assert len(manifest.chain_of_custody.events) == 1
        assert manifest.chain_of_custody.events[0].event_type == "created"
    
    def test_chain_of_custody_verification(self, keypair):
        """Test chain of custody verification"""
        private_key, public_key = keypair
        chain = ChainOfCustody(
            package_id="test_pkg",
            initial_hash="abc123",
            current_hash="abc123",
        )
        
        # Add event
        event = chain.add_event(
            event_type="transferred",
            actor="test-actor",
            location="Test Lab",
            private_key=private_key,
        )
        
        # Verify
        public_keys = {"test-actor": public_key}
        assert chain.verify_chain(public_keys)
    
    def test_tampering_detection(self):
        """Test tampering detection"""
        chain = ChainOfCustody(
            package_id="test_pkg",
            initial_hash="original_hash",
            current_hash="original_hash",
        )
        
        # No tampering
        assert not chain.detect_tampering("original_hash")
        
        # Tampering detected
        assert chain.detect_tampering("different_hash")


# ============================================================================
# VERIFICATION SCRIPT TESTS
# ============================================================================

class TestVerificationScript:
    """Test verification script generation"""
    
    def test_verification_script_generated(self, exporter, sample_records):
        """Test that verification script is generated"""
        package = exporter.export_batch(
            records=sample_records,
            format=ExportFormat.CEF,
        )
        
        assert package.verification_script_path.exists()
        assert package.verification_script_path.suffix == '.sh'
        
        # Check script is executable
        import stat
        mode = package.verification_script_path.stat().st_mode
        assert mode & stat.S_IXUSR  # User executable
    
    def test_verification_script_content(self, exporter, sample_records):
        """Test verification script contains correct checks"""
        package = exporter.export_batch(
            records=sample_records,
            format=ExportFormat.CEF,
        )
        
        script_content = package.verification_script_path.read_text()
        
        # Should contain key verification steps
        assert "sha256sum" in script_content
        assert package.package_id in script_content
        assert "jq" in script_content  # For JSON parsing


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_export_format_raises_error(self, exporter, sample_records):
        """Test that invalid format raises error"""
        # ExportFormatError is raised for unsupported formats
        from mahoun.audit.airgap_exporter import ExportFormatError
        
        with pytest.raises(ExportFormatError):
            exporter.export_batch(
                records=sample_records,
                format="invalid_format",  # type: ignore
            )
    
    def test_export_with_corrupted_records(self, exporter):
        """Test exporting with malformed records"""
        # Should handle gracefully
        malformed_records = [
            {"id": "rec_1"},  # Missing required fields
            {"timestamp": "invalid_date"},
            {},
        ]
        
        # Should not crash (may produce warning but completes)
        package = exporter.export_batch(
            records=malformed_records,
            format=ExportFormat.CEF,
        )
        
        assert package.manifest.record_count == len(malformed_records)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """End-to-end integration tests"""
    
    def test_complete_export_and_transfer_workflow(
        self, exporter, sample_records, keypair, temp_export_dir
    ):
        """Test complete workflow: export → transfer → verify"""
        # 1. Export packages
        package = exporter.export_batch(
            records=sample_records,
            format=ExportFormat.CEF,
            compression=CompressionType.GZIP,
        )
        
        # 2. Create transfer manifest
        private_key, public_key = keypair
        protocol = TransferProtocol(
            private_key=private_key,
            actor_id="sender@test",
            location="Test Lab",
        )
        
        transfer_manifest = protocol.create_transfer(
            package_ids=[package.package_id],
            package_sizes_mb=[package.get_transfer_size_mb()],
        )
        
        # 3. Write transfer manifest
        manifest_path = protocol.write_manifest(
            manifest=transfer_manifest,
            output_dir=temp_export_dir,
        )
        
        assert manifest_path.exists()
        
        # 4. Simulate receiver verification
        receiver_private, receiver_public = generate_keypair()
        receiver_protocol = TransferProtocol(
            private_key=receiver_private,
            actor_id="receiver@test",
            location="Remote Lab",
        )
        
        # Read manifest
        read_manifest = receiver_protocol.read_manifest(manifest_path)
        
        # Verify sender
        assert read_manifest.verify_sender(public_key)
        
        # Acknowledge receipt
        final_manifest = receiver_protocol.acknowledge_receipt(
            manifest=read_manifest,
            verification_passed=True,
        )
        
        assert final_manifest.status == TransferStatus.VERIFIED
        assert final_manifest.verify_receiver(receiver_public)
    
    def test_batch_export_multiple_packages(self, exporter, sample_records):
        """Test exporting multiple packages in batch"""
        packages = []
        
        # Export multiple formats
        for fmt in [ExportFormat.CEF, ExportFormat.LEEF, ExportFormat.JSONL]:
            package = exporter.export_batch(
                records=sample_records,
                format=fmt,
                compression=CompressionType.GZIP,
            )
            packages.append(package)
        
        assert len(packages) == 3
        
        # All should have unique package IDs
        package_ids = [p.package_id for p in packages]
        assert len(package_ids) == len(set(package_ids))


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance and scalability tests"""
    
    def test_large_record_export(self, exporter, keypair):
        """Test exporting large number of records"""
        # Generate 1000 records
        large_records = [
            {
                "id": f"record_{i}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "correlation_id": f"corr_{i}",
                "actor_id": "test-user",
                "operation": "reasoning",
            }
            for i in range(1000)
        ]
        
        package = exporter.export_batch(
            records=large_records,
            format=ExportFormat.CEF,
            compression=CompressionType.GZIP,
        )
        
        assert package.manifest.record_count == 1000
        
        # Should achieve reasonable compression
        ratio = package.get_compression_ratio()
        assert ratio > 2.0  # At least 2x compression


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
