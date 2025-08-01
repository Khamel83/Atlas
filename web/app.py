import datetime
import glob
import os
from urllib.parse import urlencode

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ask.insights.pattern_detector import PatternDetector
# --- Cognitive Amplification (Ask) Subsystem Endpoints ---
from ask.proactive.surfacer import ProactiveSurfacer
from ask.recall.recall_engine import RecallEngine
from ask.socratic.question_engine import QuestionEngine
from ask.temporal.temporal_engine import TemporalEngine
from helpers.metadata_manager import MetadataManager


# For demo: instantiate with default config (replace with real config/manager in production)
def get_metadata_manager():
    try:
        from helpers.config import load_config

        config = load_config()
    except Exception:
        config = {}
    return MetadataManager(config)


app = FastAPI(title="Atlas Scheduler Web Interface")

templates = Jinja2Templates(directory="web/templates")

# Path to the scheduler's SQLite job store (should match Atlas scheduler)
JOBSTORE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scheduler.db"
)  # Unified job store for persistence

# Simple in-memory log for job runs (MVP)
job_logs = {}


def log_job_run(job_id, message):
    """Append a log entry for a job (in-memory, last 50 entries)."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    job_logs.setdefault(job_id, []).append(f"[{now}] {message}")
    job_logs[job_id] = job_logs[job_id][-50:]


# APScheduler instance (paused, for inspection and management only)
scheduler = BackgroundScheduler(
    jobstores={"default": SQLAlchemyJobStore(url=f"sqlite:///{JOBSTORE_PATH}")}
)
scheduler.start(paused=True)


# Dummy function for new jobs (MVP)
def dummy_job():
    """A placeholder job function for demonstration purposes."""
    log_job_run("dummy", "Dummy job executed.")
    print("Dummy job executed.")


# Map job IDs to their log file paths for ingestion jobs
INGESTION_LOG_PATHS = {
    "weekly_article_ingestion": os.path.join(
        os.path.dirname(__file__), "..", "output", "articles", "ingest.log"
    ),
    "weekly_podcast_ingestion": os.path.join(
        os.path.dirname(__file__), "..", "output", "podcasts", "ingest.log"
    ),
    "weekly_youtube_ingestion": os.path.join(
        os.path.dirname(__file__), "..", "output", "youtube", "ingest.log"
    ),
}


def read_log_tail(log_path, n=50):
    """Read the last n lines from a log file."""
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
        return lines[-n:]
    except Exception:
        return ["No log file found or unable to read log."]


@app.get("/", response_class=HTMLResponse)
def root():
    """Landing page with a link to the jobs UI and cognitive dashboard."""
    return """
    <h1>Atlas Scheduler Web Interface</h1>
    <p>Welcome! Use the <a href='/jobs/html'>/jobs/html</a> endpoint to view scheduled jobs (MVP).</p>
    <p>Explore <a href='/ask/html'>Cognitive Amplification Dashboard</a> for advanced features.</p>
    """


@app.get("/jobs", response_class=JSONResponse)
def list_jobs():
    """Return all jobs as JSON (API endpoint)."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time),
                "trigger": str(job.trigger),
                "func": str(job.func_ref),
                "args": job.args,
                "kwargs": job.kwargs,
                "enabled": not job.paused if hasattr(job, "paused") else True,
            }
        )
    return {"jobs": jobs}


# Enhance jobs_html to show last run status and timestamp for ingestion jobs
@app.get("/jobs/html", response_class=HTMLResponse)
def jobs_html(request: Request, msg: str = "", error: str = ""):
    """Main jobs UI: list jobs, show messages/errors."""
    jobs = []
    for job in scheduler.get_jobs():
        job_info = {
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time),
            "trigger": str(job.trigger),
            "func": str(job.func_ref),
            "args": job.args,
            "kwargs": job.kwargs,
            "enabled": not job.paused if hasattr(job, "paused") else True,
        }
        # For ingestion jobs, try to get last run status and timestamp from log file
        if job.id in INGESTION_LOG_PATHS:
            log_path = INGESTION_LOG_PATHS[job.id]
            try:
                with open(log_path, "r") as f:
                    lines = f.readlines()
                # Look for last status line
                last_status = None
                last_time = None
                for line in reversed(lines):
                    if "ingestion complete" in line.lower() or "error" in line.lower():
                        last_status = (
                            "Success" if "complete" in line.lower() else "Error"
                        )
                        # Try to extract timestamp if present
                        if line.startswith("["):
                            last_time = line.split("]")[0].strip("[]")
                        break
                job_info["last_status"] = last_status or "Unknown"
                job_info["last_time"] = last_time or "-"
            except Exception:
                job_info["last_status"] = "-"
                job_info["last_time"] = "-"
        else:
            job_info["last_status"] = "-"
            job_info["last_time"] = "-"
        jobs.append(job_info)
    return templates.TemplateResponse(
        "jobs.html", {"request": request, "jobs": jobs, "msg": msg, "error": error}
    )


@app.get("/jobs/{job_id}/edit", response_class=HTMLResponse)
def edit_job_form(request: Request, job_id: str, msg: str = "", error: str = ""):
    """Render the edit form for a job (cron string only)."""
    job = scheduler.get_job(job_id)
    if not job:
        return RedirectResponse(url="/jobs/html?error=Job+not+found", status_code=303)
    cron_str = (
        job.trigger.cronspec if hasattr(job.trigger, "cronspec") else str(job.trigger)
    )
    return templates.TemplateResponse(
        "edit_job.html",
        {
            "request": request,
            "job": {"id": job.id, "name": job.name, "cron": cron_str},
            "msg": msg,
            "error": error,
        },
    )


@app.post("/jobs/{job_id}/edit")
def edit_job(job_id: str, cron: str = Form(...)):
    """Update a job's cron schedule."""
    job = scheduler.get_job(job_id)
    if job:
        try:
            trigger = CronTrigger.from_crontab(cron)
            scheduler.reschedule_job(job_id, trigger=trigger)
            log_job_run(job_id, f"Job rescheduled to cron: {cron}")
            params = urlencode({"msg": "Job updated."})
            return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)
        except Exception as e:
            print(f"Error editing job: {e}")
            params = urlencode({"error": f"Invalid cron string: {cron}"})
            return RedirectResponse(
                url=f"/jobs/{job_id}/edit?{params}", status_code=303
            )
    return RedirectResponse(url="/jobs/html", status_code=303)


@app.post("/jobs/{job_id}/trigger")
def trigger_job(job_id: str):
    """Manually trigger a job to run immediately."""
    job = scheduler.get_job(job_id)
    if job:
        try:
            job.modify(next_run_time=None)
            scheduler.wakeup()
            log_job_run(job_id, "Job manually triggered.")
            params = urlencode({"msg": "Job triggered."})
            return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)
        except Exception as e:
            print(f"Error triggering job: {e}")
            params = urlencode({"error": "Failed to trigger job."})
            return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)
    return RedirectResponse(url="/jobs/html", status_code=303)


@app.get("/jobs/{job_id}/logs", response_class=HTMLResponse)
def job_logs(request: Request, job_id: str):
    """Show logs for a job. For ingestion jobs, show real log file; otherwise, show in-memory log."""
    if job_id in INGESTION_LOG_PATHS:
        log_path = INGESTION_LOG_PATHS[job_id]
        logs = read_log_tail(log_path)
    else:
        logs = job_logs.get(job_id, ["No logs for this job yet."])
    return templates.TemplateResponse(
        "logs.html", {"request": request, "job_id": job_id, "logs": logs}
    )


@app.post("/jobs/{job_id}/enable")
def enable_job(job_id: str):
    """Enable (resume) a paused job."""
    job = scheduler.get_job(job_id)
    if job:
        scheduler.resume_job(job_id)
        log_job_run(job_id, "Job enabled.")
        params = urlencode({"msg": "Job enabled."})
        return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)
    return RedirectResponse(url="/jobs/html", status_code=303)


@app.post("/jobs/{job_id}/disable")
def disable_job(job_id: str):
    """Disable (pause) a job."""
    job = scheduler.get_job(job_id)
    if job:
        scheduler.pause_job(job_id)
        log_job_run(job_id, "Job disabled.")
        params = urlencode({"msg": "Job disabled."})
        return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)
    return RedirectResponse(url="/jobs/html", status_code=303)


@app.post("/jobs/{job_id}/delete")
def delete_job(job_id: str):
    """Delete a job from the scheduler."""
    scheduler.remove_job(job_id)
    log_job_run(job_id, "Job deleted.")
    params = urlencode({"msg": "Job deleted."})
    return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)


@app.post("/jobs/add")
def add_job(name: str = Form(...), cron: str = Form(...)):
    """Add a new job with the given name and cron string (dummy function)."""
    try:
        trigger = CronTrigger.from_crontab(cron)
        scheduler.add_job(dummy_job, trigger, id=name, name=name, replace_existing=True)
        log_job_run(name, f"Job added with cron: {cron}")
        params = urlencode({"msg": "Job added."})
        return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)
    except Exception as e:
        print(f"Error adding job: {e}")
        params = urlencode({"error": f"Invalid cron string: {cron}"})
        return RedirectResponse(url=f"/jobs/html?{params}", status_code=303)


# Future endpoints:
# - GET /jobs/{job_id}/logs (view logs)


@app.get("/ask/proactive", response_class=JSONResponse)
def ask_proactive():
    """Surface forgotten/stale content (top 5)."""
    mgr = get_metadata_manager()
    surfacer = ProactiveSurfacer(mgr)
    items = surfacer.surface_forgotten_content(n=5)
    return {
        "forgotten": [
            {
                "title": getattr(i, "title", None),
                "updated_at": getattr(i, "updated_at", None),
            }
            for i in items
        ]
    }


@app.get("/ask/temporal", response_class=JSONResponse)
def ask_temporal():
    """Show time-aware content relationships (max 10)."""
    mgr = get_metadata_manager()
    engine = TemporalEngine(mgr)
    rels = engine.get_time_aware_relationships(max_delta_days=2)
    return {
        "relationships": [
            {
                "from": getattr(a, "title", None),
                "to": getattr(b, "title", None),
                "days": d,
            }
            for a, b, d in rels[:10]
        ]
    }


@app.post("/ask/socratic", response_class=JSONResponse)
def ask_socratic(content: str = Form(...)):
    """Generate Socratic questions from content."""
    engine = QuestionEngine()
    questions = engine.generate_questions(content)
    return {"questions": questions}


@app.get("/ask/recall", response_class=JSONResponse)
def ask_recall():
    """Show most overdue items for spaced repetition (top 5)."""
    mgr = get_metadata_manager()
    engine = RecallEngine(mgr)
    items = engine.schedule_spaced_repetition(n=5)
    return {
        "due_for_review": [
            {
                "title": getattr(i, "title", None),
                "last_reviewed": getattr(i, "type_specific", {}).get(
                    "last_reviewed", None
                ),
            }
            for i in items
        ]
    }


@app.get("/ask/patterns", response_class=JSONResponse)
def ask_patterns():
    """Show top tags and sources (top 5)."""
    mgr = get_metadata_manager()
    detector = PatternDetector(mgr)
    patterns = detector.find_patterns(n=5)
    return {"top_tags": patterns["top_tags"], "top_sources": patterns["top_sources"]}


@app.get("/ask/html", response_class=HTMLResponse)
async def ask_dashboard(request: Request, feature: str = ""):
    """Render the cognitive amplification dashboard with the selected feature."""
    mgr = get_metadata_manager()
    data = None
    if feature == "proactive":
        surfacer = ProactiveSurfacer(mgr)
        data = {
            "forgotten": [
                {
                    "title": getattr(i, "title", None),
                    "updated_at": getattr(i, "updated_at", None),
                }
                for i in surfacer.surface_forgotten_content(n=5)
            ]
        }
    elif feature == "temporal":
        engine = TemporalEngine(mgr)
        rels = engine.get_time_aware_relationships(max_delta_days=2)
        data = {
            "relationships": [
                {
                    "from": getattr(a, "title", None),
                    "to": getattr(b, "title", None),
                    "days": d,
                }
                for a, b, d in rels[:10]
            ]
        }
    elif feature == "recall":
        engine = RecallEngine(mgr)
        items = engine.schedule_spaced_repetition(n=5)
        data = {
            "due_for_review": [
                {
                    "title": getattr(i, "title", None),
                    "last_reviewed": getattr(i, "type_specific", {}).get(
                        "last_reviewed", None
                    ),
                }
                for i in items
            ]
        }
    elif feature == "patterns":
        detector = PatternDetector(mgr)
        patterns = detector.find_patterns(n=5)
        data = {
            "top_tags": patterns["top_tags"],
            "top_sources": patterns["top_sources"],
        }
    # Socratic handled by POST
    return templates.TemplateResponse(
        "ask_dashboard.html", {"request": request, "feature": feature, "data": data}
    )


@app.post("/ask/html", response_class=HTMLResponse)
async def ask_dashboard_post(
    request: Request, feature: str = Form(""), content: str = Form("")
):
    """Handle Socratic question form submission."""
    data = None
    if feature == "socratic" and content:
        engine = QuestionEngine()
        questions = engine.generate_questions(content)
        data = {"questions": questions}
    return templates.TemplateResponse(
        "ask_dashboard.html", {"request": request, "feature": feature, "data": data}
    )
