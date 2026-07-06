"""
Scheduled Data Quality Validation
==================================

Automated weekly validation job for knowledge graph data quality.
"""

import logging
import schedule
import time
from datetime import datetime
from pathlib import Path

from graph.neo4j.connection import Neo4jConnection
from graph.validation.data_quality import DataQualityValidator

logger = logging.getLogger(__name__)


class ScheduledValidator:
    """
    Scheduled validation job runner
    
    Runs data quality validation on a schedule and saves reports.
    """
    
    def __init__(
        self,
        output_dir: str = "data/quality_reports",
        schedule_time: str = "02:00"  # 2 AM
    ):
        """
        Initialize scheduled validator
        
        Args:
            output_dir: Directory to save reports
            schedule_time: Time to run validation (HH:MM format)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.schedule_time = schedule_time
        self.connection = None
    
    def run_validation(self):
        """Run validation and save report"""
        try:
            logger.info("Starting scheduled data quality validation...")
            
            # Connect to Neo4j
            if not self.connection:
                self.connection = Neo4jConnection()
            
            # Create validator
            validator = DataQualityValidator(self.connection)
            
            # Run validation
            report = validator.validate_all()
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = self.output_dir / f"quality_report_{timestamp}.txt"
            
            # Save report
            validator.generate_report(str(report_file))
            
            logger.info(
                f"Validation complete: {report['quality_level']} quality "
                f"(score={report['quality_score']}, issues={report['total_issues']})"
            )
            logger.info(f"Report saved to {report_file}")
            
            # Clean up old reports (keep last 7)
            self._cleanup_old_reports()
            
            return report
        
        except Exception as e:
            logger.error(f"Scheduled validation failed: {e}", exc_info=True)
            return None
    
    def _cleanup_old_reports(self, keep_count: int = 7):
        """
        Clean up old reports, keeping only the most recent ones
        
        Args:
            keep_count: Number of reports to keep
        """
        try:
            # Get all report files sorted by modification time
            reports = sorted(
                self.output_dir.glob("quality_report_*.txt"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Delete old reports
            for report in reports[keep_count:]:
                report.unlink()
                logger.info(f"Deleted old report: {report.name}")
        
        except Exception as e:
            logger.warning(f"Failed to cleanup old reports: {e}")
    
    def start(self):
        """Start the scheduled validation job"""
        logger.info(f"Starting scheduled validation at {self.schedule_time} weekly")
        
        # Schedule weekly validation
        schedule.every().sunday.at(self.schedule_time).do(self.run_validation)
        
        # Run immediately on start (optional)
        # self.run_validation()
        
        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        except KeyboardInterrupt:
            logger.info("Scheduled validation stopped")
        
        finally:
            if self.connection:
                self.connection.close()
    
    def stop(self):
        """Stop the scheduled validation job"""
        schedule.clear()
        if self.connection:
            self.connection.close()
            self.connection = None


def start_scheduled_validation(
    output_dir: str = "data/quality_reports",
    schedule_time: str = "02:00"
):
    """
    Start scheduled validation job
    
    Args:
        output_dir: Directory to save reports
        schedule_time: Time to run validation (HH:MM format)
    """
    validator = ScheduledValidator(output_dir, schedule_time)
    validator.start()


if __name__ == '__main__':
    # Run as standalone script
    import sys
    from core.logging import setup_logging
    
    setup_logging(__name__)
    
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "data/quality_reports"
    schedule_time = sys.argv[2] if len(sys.argv) > 2 else "02:00"
    
    start_scheduled_validation(output_dir, schedule_time)
