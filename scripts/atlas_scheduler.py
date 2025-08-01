#!/usr/bin/env python3
"""
Atlas Automated Scheduling System

This system provides comprehensive job scheduling capabilities for Atlas using APScheduler.
It supports:
- Monthly model discovery updates
- Weekly health checks
- Daily maintenance tasks
- Custom user-defined schedules
- Job persistence and recovery
- Web interface for job management

Usage:
    python3 scripts/atlas_scheduler.py --start        # Start scheduler daemon
    python3 scripts/atlas_scheduler.py --stop         # Stop scheduler daemon
    python3 scripts/atlas_scheduler.py --status       # Show scheduler status
    python3 scripts/atlas_scheduler.py --add-job      # Add custom job
    python3 scripts/atlas_scheduler.py --list-jobs    # List all jobs
    python3 scripts/atlas_scheduler.py --web          # Start web interface
"""

import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
    from apscheduler.executors.pool import ThreadPoolExecutor
    from apscheduler.job import Job
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
except ImportError as e:
    print(f"APScheduler import error: {e}")
    print("Please run 'pip install apscheduler'.")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Confirm, Prompt
    from rich.rule import Rule
    from rich.table import Table
    from rich.text import Text
except ImportError:
    print("Rich library not found. Please run 'pip install rich'.")
    sys.exit(1)

from helpers.config import load_config

console = Console()


class JobType(Enum):
    MODEL_DISCOVERY = "model_discovery"
    HEALTH_CHECK = "health_check"
    MAINTENANCE = "maintenance"
    INGESTION = "ingestion"
    BACKUP = "backup"
    CUSTOM = "custom"


class JobStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    SCHEDULED = "scheduled"


@dataclass
class AtlasJob:
    """Represents a scheduled job in Atlas."""

    id: str
    name: str
    job_type: JobType
    command: str
    schedule: str  # Cron expression or interval
    description: str
    enabled: bool = True
    last_run: Optional[str] = None
    last_status: Optional[JobStatus] = None
    run_count: int = 0
    failure_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


class AtlasScheduler:
    """Main Atlas scheduling system."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.config = load_config()
        self.console = console

        # Configuration
        self.jobs_file = self.project_root / "scheduler_jobs.json"
        self.logs_dir = self.project_root / "logs" / "scheduler"
        self.pid_file = self.project_root / "scheduler.pid"

        # Ensure directories exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.setup_logging()

        # Initialize scheduler
        self.scheduler = None
        self.jobs: Dict[str, AtlasJob] = {}
        self.load_jobs()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def setup_logging(self):
        """Setup logging for scheduler operations."""
        log_file = self.logs_dir / "scheduler.log"

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def load_jobs(self):
        """Load jobs from JSON file."""
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, "r") as f:
                    jobs_data = json.load(f)
                    self.jobs = {
                        job_id: AtlasJob(**job_data)
                        for job_id, job_data in jobs_data.items()
                    }
                    # Convert string enums back to enum objects
                    for job in self.jobs.values():
                        job.job_type = JobType(job.job_type)
                        if job.last_status:
                            job.last_status = JobStatus(job.last_status)
            except Exception as e:
                self.logger.error(f"Failed to load jobs: {e}")
                self.create_default_jobs()
        else:
            self.create_default_jobs()

    def save_jobs(self):
        """Save jobs to JSON file."""
        try:
            jobs_data = {}
            for job_id, job in self.jobs.items():
                job_dict = asdict(job)
                job_dict["job_type"] = job.job_type.value
                if job.last_status:
                    job_dict["last_status"] = job.last_status.value
                jobs_data[job_id] = job_dict

            with open(self.jobs_file, "w") as f:
                json.dump(jobs_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save jobs: {e}")

    def create_default_jobs(self):
        """Create default scheduled jobs."""
        default_jobs = [
            AtlasJob(
                id="monthly_model_discovery",
                name="Monthly Model Discovery Update",
                job_type=JobType.MODEL_DISCOVERY,
                command="python3 scripts/model_discovery_updater.py",
                schedule="0 0 1 * *",  # 1st of every month at midnight
                description="Discover new free models and update recommendations",
            ),
            AtlasJob(
                id="weekly_health_check",
                name="Weekly Health Check",
                job_type=JobType.HEALTH_CHECK,
                command="python3 scripts/health_check.py",
                schedule="0 9 * * 1",  # Every Monday at 9 AM
                description="Run comprehensive health check and generate report",
            ),
            AtlasJob(
                id="daily_maintenance",
                name="Daily Maintenance",
                job_type=JobType.MAINTENANCE,
                command="python3 scripts/maintenance.py",
                schedule="0 2 * * *",  # Every day at 2 AM
                description="Clean logs, optimize database, check disk space",
            ),
            AtlasJob(
                id="daily_backup",
                name="Daily Backup",
                job_type=JobType.BACKUP,
                command="python3 scripts/backup.py",
                schedule="0 3 * * *",  # Every day at 3 AM
                description="Backup configuration and important data",
            ),
            AtlasJob(
                id="weekly_article_ingestion",
                name="Weekly Article Ingestion",
                job_type=JobType.INGESTION,
                command="python3 run.py --articles",
                schedule="0 10 * * 2",  # Every Tuesday at 10 AM
                description="Process articles from inputs/articles.txt",
            ),
            AtlasJob(
                id="weekly_podcast_ingestion",
                name="Weekly Podcast Ingestion",
                job_type=JobType.INGESTION,
                command="python3 run.py --podcasts",
                schedule="0 11 * * 2",  # Every Tuesday at 11 AM
                description="Process new podcast episodes",
            ),
            AtlasJob(
                id="weekly_youtube_ingestion",
                name="Weekly YouTube Ingestion",
                job_type=JobType.INGESTION,
                command="python3 run.py --youtube",
                schedule="0 12 * * 2",  # Every Tuesday at 12 PM
                description="Process YouTube videos from inputs/youtube.txt",
            ),
        ]

        for job in default_jobs:
            self.jobs[job.id] = job

        self.save_jobs()
        self.logger.info(f"Created {len(default_jobs)} default jobs")

    def initialize_scheduler(self):
        """Initialize the APScheduler instance."""
        # Configure job store (SQLite database)
        jobstores = {
            "default": SQLAlchemyJobStore(
                url=f"sqlite:///{self.project_root}/scheduler.db"
            )
        }

        # Configure executors
        executors = {
            "default": ThreadPoolExecutor(20),
        }

        # Job defaults
        job_defaults = {"coalesce": False, "max_instances": 3, "misfire_grace_time": 30}

        # Create scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

        # Add event listeners
        self.scheduler.add_listener(self.job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self.job_error, EVENT_JOB_ERROR)

        self.logger.info("Scheduler initialized")

    def start_scheduler(self):
        """Start the scheduler daemon."""
        if self.is_running():
            self.console.print("[yellow]Scheduler is already running[/yellow]")
            return False

        try:
            self.initialize_scheduler()

            # Add all enabled jobs to scheduler
            for job in self.jobs.values():
                if job.enabled:
                    self.add_job_to_scheduler(job)

            # Start scheduler
            self.scheduler.start()

            # Write PID file
            with open(self.pid_file, "w") as f:
                f.write(str(os.getpid()))

            self.logger.info("Atlas Scheduler started successfully")
            self.console.print("[green]Atlas Scheduler started successfully[/green]")

            # Keep the scheduler running
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop_scheduler()

            return True

        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
            self.console.print(f"[red]Failed to start scheduler: {e}[/red]")
            return False

    def stop_scheduler(self):
        """Stop the scheduler daemon."""
        if self.scheduler:
            self.scheduler.shutdown()
            self.logger.info("Scheduler stopped")

        # Remove PID file
        if self.pid_file.exists():
            self.pid_file.unlink()

        self.console.print("[yellow]Atlas Scheduler stopped[/yellow]")

    def is_running(self) -> bool:
        """Check if scheduler is currently running."""
        if not self.pid_file.exists():
            return False

        try:
            with open(self.pid_file, "r") as f:
                pid = int(f.read().strip())

            # Check if process is still running
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            # Process doesn't exist or PID file is corrupted
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False

    def add_job_to_scheduler(self, job: AtlasJob):
        """Add a job to the APScheduler."""
        if not self.scheduler:
            return

        try:
            # Parse cron expression
            cron_parts = job.schedule.split()
            if len(cron_parts) == 5:
                minute, hour, day, month, day_of_week = cron_parts
                trigger = CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week,
                )
            else:
                # Try to parse as interval (e.g., "30m", "1h", "1d")
                trigger = self.parse_interval(job.schedule)

            # Add job to scheduler
            self.scheduler.add_job(
                func=self.execute_job,
                trigger=trigger,
                args=[job.id],
                id=job.id,
                name=job.name,
                replace_existing=True,
            )

            self.logger.info(f"Added job to scheduler: {job.id}")

        except Exception as e:
            self.logger.error(f"Failed to add job {job.id} to scheduler: {e}")

    def parse_interval(self, schedule: str) -> IntervalTrigger:
        """Parse interval string (e.g., '30m', '1h', '1d') into IntervalTrigger."""
        if schedule.endswith("m"):
            minutes = int(schedule[:-1])
            return IntervalTrigger(minutes=minutes)
        elif schedule.endswith("h"):
            hours = int(schedule[:-1])
            return IntervalTrigger(hours=hours)
        elif schedule.endswith("d"):
            days = int(schedule[:-1])
            return IntervalTrigger(days=days)
        else:
            raise ValueError(f"Invalid interval format: {schedule}")

    def execute_job(self, job_id: str):
        """Execute a scheduled job."""
        if job_id not in self.jobs:
            self.logger.error(f"Job not found: {job_id}")
            return

        job = self.jobs[job_id]
        self.logger.info(f"Executing job: {job_id}")

        # Update job status
        job.last_run = datetime.now().isoformat()
        job.run_count += 1

        try:
            # Execute the command
            result = subprocess.run(
                job.command,
                shell=True,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )

            if result.returncode == 0:
                job.last_status = JobStatus.COMPLETED
                self.logger.info(f"Job {job_id} completed successfully")
            else:
                job.last_status = JobStatus.FAILED
                job.failure_count += 1
                self.logger.error(
                    f"Job {job_id} failed with exit code {result.returncode}"
                )
                self.logger.error(f"STDERR: {result.stderr}")

        except subprocess.TimeoutExpired:
            job.last_status = JobStatus.FAILED
            job.failure_count += 1
            self.logger.error(f"Job {job_id} timed out")

        except Exception as e:
            job.last_status = JobStatus.FAILED
            job.failure_count += 1
            self.logger.error(f"Job {job_id} failed with exception: {e}")

        finally:
            # Save job status
            self.save_jobs()

    def job_executed(self, event):
        """Handle job execution event."""
        job_id = event.job_id
        self.logger.info(f"Job executed: {job_id}")

    def job_error(self, event):
        """Handle job error event."""
        job_id = event.job_id
        self.logger.error(f"Job error: {job_id} - {event.exception}")

    def signal_handler(self, signum, frame):
        """Handle termination signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop_scheduler()
        sys.exit(0)

    def add_job(self, job: AtlasJob):
        """Add a new job to the system."""
        self.jobs[job.id] = job
        self.save_jobs()

        if self.scheduler and job.enabled:
            self.add_job_to_scheduler(job)

        self.logger.info(f"Added job: {job.id}")

    def remove_job(self, job_id: str):
        """Remove a job from the system."""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self.save_jobs()

            if self.scheduler:
                try:
                    self.scheduler.remove_job(job_id)
                except:
                    pass

            self.logger.info(f"Removed job: {job_id}")
            return True
        return False

    def enable_job(self, job_id: str):
        """Enable a job."""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = True
            self.save_jobs()

            if self.scheduler:
                self.add_job_to_scheduler(self.jobs[job_id])

            return True
        return False

    def disable_job(self, job_id: str):
        """Disable a job."""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = False
            self.save_jobs()

            if self.scheduler:
                try:
                    self.scheduler.remove_job(job_id)
                except:
                    pass

            return True
        return False

    def list_jobs(self):
        """Display all jobs in a formatted table."""
        table = Table(title="Atlas Scheduled Jobs")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Type", style="magenta")
        table.add_column("Schedule", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Last Run", style="blue")
        table.add_column("Runs", style="white")
        table.add_column("Failures", style="red")

        for job in self.jobs.values():
            status = "Enabled" if job.enabled else "Disabled"
            if job.last_status:
                status = f"{status} ({job.last_status.value})"

            last_run = "Never"
            if job.last_run:
                last_run = datetime.fromisoformat(job.last_run).strftime(
                    "%Y-%m-%d %H:%M"
                )

            table.add_row(
                job.id,
                job.name,
                job.job_type.value,
                job.schedule,
                status,
                last_run,
                str(job.run_count),
                str(job.failure_count),
            )

        console.print(table)

    def show_status(self):
        """Show scheduler status."""
        running = self.is_running()

        status_panel = Panel(
            f"Scheduler Status: {'[green]Running[/green]' if running else '[red]Stopped[/red]'}\n"
            f"Total Jobs: {len(self.jobs)}\n"
            f"Enabled Jobs: {sum(1 for job in self.jobs.values() if job.enabled)}\n"
            f"PID File: {self.pid_file}",
            title="Atlas Scheduler Status",
        )

        console.print(status_panel)

        if running and self.scheduler:
            # Show next scheduled jobs
            next_jobs = self.scheduler.get_jobs()
            if next_jobs:
                console.print("\n[cyan]Next Scheduled Jobs:[/cyan]")
                for job in next_jobs[:5]:  # Show next 5 jobs
                    next_run = (
                        job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                        if job.next_run_time
                        else "Unknown"
                    )
                    console.print(f"  • {job.name}: {next_run}")

    def interactive_mode(self):
        """Run interactive mode for managing jobs."""
        while True:
            console.print(Rule("[bold blue]Atlas Scheduler Management", style="blue"))

            options = [
                "1. Show status",
                "2. List all jobs",
                "3. Start scheduler",
                "4. Stop scheduler",
                "5. Add custom job",
                "6. Enable/disable job",
                "7. Remove job",
                "8. Exit",
            ]

            for option in options:
                console.print(option)

            choice = Prompt.ask(
                "Choose an option", choices=["1", "2", "3", "4", "5", "6", "7", "8"]
            )

            if choice == "1":
                self.show_status()
            elif choice == "2":
                self.list_jobs()
            elif choice == "3":
                if not self.is_running():
                    console.print(
                        "[yellow]Starting scheduler in background...[/yellow]"
                    )
                    subprocess.Popen([sys.executable, __file__, "--start"])
                else:
                    console.print("[yellow]Scheduler is already running[/yellow]")
            elif choice == "4":
                if self.is_running():
                    subprocess.run([sys.executable, __file__, "--stop"])
                else:
                    console.print("[yellow]Scheduler is not running[/yellow]")
            elif choice == "5":
                self._add_custom_job()
            elif choice == "6":
                self._toggle_job()
            elif choice == "7":
                self._remove_job()
            elif choice == "8":
                break

            console.print("\n")

    def _add_custom_job(self):
        """Interactive job creation."""
        console.print("[cyan]Add Custom Job[/cyan]")

        job_id = Prompt.ask("Job ID")
        if job_id in self.jobs:
            console.print("[red]Job ID already exists[/red]")
            return

        name = Prompt.ask("Job Name")
        command = Prompt.ask("Command to execute")
        schedule = Prompt.ask(
            "Schedule (cron format or interval like '30m', '1h', '1d')"
        )
        description = Prompt.ask("Description", default="")

        job = AtlasJob(
            id=job_id,
            name=name,
            job_type=JobType.CUSTOM,
            command=command,
            schedule=schedule,
            description=description,
        )

        self.add_job(job)
        console.print(f"[green]Job {job_id} added successfully[/green]")

    def _toggle_job(self):
        """Toggle job enabled/disabled status."""
        if not self.jobs:
            console.print("[yellow]No jobs available[/yellow]")
            return

        job_id = Prompt.ask("Job ID to toggle", choices=list(self.jobs.keys()))
        job = self.jobs[job_id]

        if job.enabled:
            self.disable_job(job_id)
            console.print(f"[yellow]Job {job_id} disabled[/yellow]")
        else:
            self.enable_job(job_id)
            console.print(f"[green]Job {job_id} enabled[/green]")

    def _remove_job(self):
        """Remove a job."""
        if not self.jobs:
            console.print("[yellow]No jobs available[/yellow]")
            return

        job_id = Prompt.ask("Job ID to remove", choices=list(self.jobs.keys()))

        if Confirm.ask(f"Are you sure you want to remove job {job_id}?"):
            self.remove_job(job_id)
            console.print(f"[red]Job {job_id} removed[/red]")


def main():
    """Main entry point for Atlas Scheduler."""
    scheduler = AtlasScheduler()

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--start":
            scheduler.start_scheduler()
        elif arg == "--stop":
            if scheduler.is_running():
                # Send SIGTERM to the running scheduler
                try:
                    with open(scheduler.pid_file, "r") as f:
                        pid = int(f.read().strip())
                    os.kill(pid, signal.SIGTERM)
                    console.print("[yellow]Scheduler stop signal sent[/yellow]")
                except:
                    console.print("[red]Failed to stop scheduler[/red]")
            else:
                console.print("[yellow]Scheduler is not running[/yellow]")
        elif arg == "--status":
            scheduler.show_status()
        elif arg == "--list-jobs":
            scheduler.list_jobs()
        elif arg == "--add-job":
            scheduler._add_custom_job()
        elif arg == "--interactive":
            scheduler.interactive_mode()
        else:
            console.print(f"[red]Unknown argument: {arg}[/red]")
            console.print(
                "Available arguments: --start, --stop, --status, --list-jobs, --add-job, --interactive"
            )
            sys.exit(1)
    else:
        # Default to interactive mode
        scheduler.interactive_mode()


if __name__ == "__main__":
    main()
