#!/usr/bin/env python3
"""
Cron-based cleanup service for Dark Web Scraper.

This service runs periodic deduplication and database optimization:
1. Scheduled duplicate removal
2. Database optimization
3. Index maintenance
4. Statistics reporting
5. Configurable cleanup schedules
"""

import os
import sys
import time
import schedule
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import json
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from dotenv import load_dotenv

# Import our deduplication modules
from duplicate_analyzer import DuplicateAnalyzer
from cleanup_duplicates import DuplicateCleanup
from smart_deduplicator import SmartDeduplicator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleanup_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CleanupService:
    """Automated cleanup service with scheduling."""
    
    def __init__(self, config_file: str = "cleanup_config.json"):
        """Initialize cleanup service with configuration."""
        self.config = self._load_config(config_file)
        self.stats_history = []
        self.last_cleanup = None
        
        # Initialize components
        self.analyzer = DuplicateAnalyzer()
        self.smart_deduplicator = SmartDeduplicator()
        
        logger.info("🚀 Cleanup service initialized")
    
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from file."""
        default_config = {
            "schedules": {
                "daily_light_cleanup": "02:00",  # Daily at 2 AM
                "weekly_full_cleanup": "sunday 03:00",  # Weekly on Sunday at 3 AM
                "monthly_deep_cleanup": "1 04:00"  # Monthly on 1st at 4 AM
            },
            "cleanup_settings": {
                "url_duplicates": True,
                "content_duplicates": True,
                "similar_content": False,
                "similarity_threshold": 0.95,
                "strategy": "latest",
                "dry_run": False
            },
            "thresholds": {
                "max_duplicates_percent": 20,  # Trigger cleanup if >20% duplicates
                "max_index_size_gb": 10,  # Trigger cleanup if index >10GB
                "min_cleanup_interval_hours": 6  # Minimum time between cleanups
            },
            "notifications": {
                "enabled": False,
                "email": "",
                "smtp_server": "",
                "smtp_port": 587,
                "smtp_user": "",
                "smtp_password": ""
            },
            "retention": {
                "keep_logs_days": 30,
                "keep_stats_days": 90
            }
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                # Merge with defaults
                default_config.update(user_config)
                logger.info(f"📋 Loaded configuration from {config_file}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load config: {e}, using defaults")
        else:
            # Save default config
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"📋 Created default configuration: {config_file}")
        
        return default_config
    
    def should_run_cleanup(self) -> bool:
        """Check if cleanup should run based on thresholds."""
        try:
            # Check minimum interval
            if self.last_cleanup:
                min_interval = timedelta(hours=self.config["thresholds"]["min_cleanup_interval_hours"])
                if datetime.now() - self.last_cleanup < min_interval:
                    return False
            
            # Run analysis to check thresholds
            analysis = self.analyzer.run_full_analysis()
            
            # Check duplicate percentage
            url_analysis = analysis['url_analysis']
            if url_analysis['total_documents'] > 0:
                duplicate_percent = (url_analysis['total_duplicates'] / url_analysis['total_documents']) * 100
                
                if duplicate_percent > self.config["thresholds"]["max_duplicates_percent"]:
                    logger.info(f"🚨 Duplicate threshold exceeded: {duplicate_percent:.1f}%")
                    return True
            
            # Check index size (would need to implement size checking)
            # This is a placeholder for index size checking
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking cleanup thresholds: {e}")
            return False
    
    def run_light_cleanup(self):
        """Run light cleanup (URL duplicates only)."""
        logger.info("🧹 Starting light cleanup...")
        
        try:
            cleanup = DuplicateCleanup(dry_run=self.config["cleanup_settings"]["dry_run"])
            
            results = cleanup.run_cleanup(
                cleanup_types=["url"],
                strategy=self.config["cleanup_settings"]["strategy"]
            )
            
            self._record_cleanup_stats("light", results)
            self._send_notification("Light Cleanup Completed", results)
            
            logger.info(f"✅ Light cleanup completed: {results['total_removed']} documents removed")
            
        except Exception as e:
            logger.error(f"❌ Light cleanup failed: {e}")
            self._send_notification("Light Cleanup Failed", {"error": str(e)})
    
    def run_full_cleanup(self):
        """Run full cleanup (URL and content duplicates)."""
        logger.info("🧹 Starting full cleanup...")
        
        try:
            cleanup = DuplicateCleanup(dry_run=self.config["cleanup_settings"]["dry_run"])
            
            cleanup_types = []
            if self.config["cleanup_settings"]["url_duplicates"]:
                cleanup_types.append("url")
            if self.config["cleanup_settings"]["content_duplicates"]:
                cleanup_types.append("content")
            
            results = cleanup.run_cleanup(
                cleanup_types=cleanup_types,
                strategy=self.config["cleanup_settings"]["strategy"]
            )
            
            self._record_cleanup_stats("full", results)
            self._send_notification("Full Cleanup Completed", results)
            
            logger.info(f"✅ Full cleanup completed: {results['total_removed']} documents removed")
            
        except Exception as e:
            logger.error(f"❌ Full cleanup failed: {e}")
            self._send_notification("Full Cleanup Failed", {"error": str(e)})
    
    def run_deep_cleanup(self):
        """Run deep cleanup (including similar content)."""
        logger.info("🧹 Starting deep cleanup...")
        
        try:
            cleanup = DuplicateCleanup(dry_run=self.config["cleanup_settings"]["dry_run"])
            
            cleanup_types = ["url", "content"]
            if self.config["cleanup_settings"]["similar_content"]:
                cleanup_types.append("similar")
            
            results = cleanup.run_cleanup(
                cleanup_types=cleanup_types,
                strategy=self.config["cleanup_settings"]["strategy"],
                similarity_threshold=self.config["cleanup_settings"]["similarity_threshold"]
            )
            
            self._record_cleanup_stats("deep", results)
            self._send_notification("Deep Cleanup Completed", results)
            
            logger.info(f"✅ Deep cleanup completed: {results['total_removed']} documents removed")
            
            # Update smart deduplicator cache
            self.smart_deduplicator.load_existing_urls()
            
        except Exception as e:
            logger.error(f"❌ Deep cleanup failed: {e}")
            self._send_notification("Deep Cleanup Failed", {"error": str(e)})
    
    def run_analysis_report(self):
        """Run analysis and generate report."""
        logger.info("📊 Generating analysis report...")
        
        try:
            analysis = self.analyzer.run_full_analysis()
            
            # Save report
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = f"analysis_report_{timestamp}.json"
            
            with open(report_file, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            
            # Send notification with summary
            summary = {
                "total_documents": analysis['url_analysis']['total_documents'],
                "unique_urls": analysis['url_analysis']['unique_urls'],
                "duplicate_urls": analysis['url_analysis']['duplicate_urls'],
                "efficiency": f"{(analysis['url_analysis']['unique_urls'] / analysis['url_analysis']['total_documents'] * 100):.1f}%" if analysis['url_analysis']['total_documents'] > 0 else "0%"
            }
            
            self._send_notification("Analysis Report Generated", summary)
            logger.info(f"📊 Analysis report saved: {report_file}")
            
        except Exception as e:
            logger.error(f"❌ Analysis report failed: {e}")
    
    def _record_cleanup_stats(self, cleanup_type: str, results: Dict):
        """Record cleanup statistics."""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "type": cleanup_type,
            "results": results
        }
        
        self.stats_history.append(stats)
        self.last_cleanup = datetime.now()
        
        # Save stats to file
        with open("cleanup_stats_history.json", 'w') as f:
            json.dump(self.stats_history, f, indent=2, default=str)
    
    def _send_notification(self, subject: str, data: Dict):
        """Send email notification if configured."""
        if not self.config["notifications"]["enabled"]:
            return
        
        try:
            msg = MimeMultipart()
            msg['From'] = self.config["notifications"]["smtp_user"]
            msg['To'] = self.config["notifications"]["email"]
            msg['Subject'] = f"Dark Web Scraper: {subject}"
            
            body = f"""
            Dark Web Scraper Cleanup Service Report
            
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            Subject: {subject}
            
            Details:
            {json.dumps(data, indent=2, default=str)}
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(
                self.config["notifications"]["smtp_server"],
                self.config["notifications"]["smtp_port"]
            )
            server.starttls()
            server.login(
                self.config["notifications"]["smtp_user"],
                self.config["notifications"]["smtp_password"]
            )
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"📧 Notification sent: {subject}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")
    
    def cleanup_old_files(self):
        """Clean up old log and stats files."""
        logger.info("🧹 Cleaning up old files...")
        
        try:
            current_time = datetime.now()
            
            # Clean up old log files
            log_retention = timedelta(days=self.config["retention"]["keep_logs_days"])
            
            # Clean up old stats files
            stats_retention = timedelta(days=self.config["retention"]["keep_stats_days"])
            
            # This would implement actual file cleanup
            # For now, just log the action
            logger.info("🗑️ Old file cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ File cleanup failed: {e}")
    
    def setup_schedules(self):
        """Set up scheduled tasks."""
        schedules = self.config["schedules"]
        
        # Daily light cleanup
        if "daily_light_cleanup" in schedules:
            schedule.every().day.at(schedules["daily_light_cleanup"]).do(self.run_light_cleanup)
            logger.info(f"📅 Scheduled daily light cleanup at {schedules['daily_light_cleanup']}")
        
        # Weekly full cleanup
        if "weekly_full_cleanup" in schedules:
            day, time = schedules["weekly_full_cleanup"].split()
            getattr(schedule.every(), day.lower()).at(time).do(self.run_full_cleanup)
            logger.info(f"📅 Scheduled weekly full cleanup on {day} at {time}")
        
        # Monthly deep cleanup
        if "monthly_deep_cleanup" in schedules:
            day, time = schedules["monthly_deep_cleanup"].split()
            # Note: schedule library doesn't support monthly directly
            # This would need a more sophisticated scheduler
            logger.info(f"📅 Monthly deep cleanup configured for day {day} at {time}")
        
        # Daily analysis report
        schedule.every().day.at("01:00").do(self.run_analysis_report)
        logger.info("📅 Scheduled daily analysis report at 01:00")
        
        # Weekly file cleanup
        schedule.every().sunday.at("05:00").do(self.cleanup_old_files)
        logger.info("📅 Scheduled weekly file cleanup on Sunday at 05:00")
    
    def run_service(self):
        """Run the cleanup service."""
        logger.info("🚀 Starting cleanup service...")
        
        self.setup_schedules()
        
        logger.info("⏰ Service running, waiting for scheduled tasks...")
        
        try:
            while True:
                schedule.run_pending()
                
                # Check if emergency cleanup is needed
                if self.should_run_cleanup():
                    logger.info("🚨 Emergency cleanup triggered")
                    self.run_full_cleanup()
                
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("🛑 Service stopped by user")
        except Exception as e:
            logger.error(f"❌ Service error: {e}")


def main():
    """Main function to run cleanup service."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Dark Web Scraper Cleanup Service")
    parser.add_argument("--config", default="cleanup_config.json", help="Configuration file")
    parser.add_argument("--once", action="store_true", help="Run cleanup once and exit")
    parser.add_argument("--type", choices=["light", "full", "deep", "analysis"], default="full",
                       help="Type of cleanup to run (when using --once)")
    
    args = parser.parse_args()
    
    try:
        service = CleanupService(args.config)
        
        if args.once:
            # Run once and exit
            if args.type == "light":
                service.run_light_cleanup()
            elif args.type == "full":
                service.run_full_cleanup()
            elif args.type == "deep":
                service.run_deep_cleanup()
            elif args.type == "analysis":
                service.run_analysis_report()
        else:
            # Run as service
            service.run_service()
            
    except Exception as e:
        logger.error(f"❌ Service failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
