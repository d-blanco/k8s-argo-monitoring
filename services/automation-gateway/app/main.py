from __future__ import annotations

import random
import time
import uuid

import time
import httpx
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(title="automation-gateway")

# ----------------------------
# Prometheus metrics (REQUIRED)
# ----------------------------
automation_jobs_total = Counter(
    "automation_jobs_total",
    "Total automation jobs completed",
    labelnames=["action", "status"],  # status: SUCCESS/FAILED
)

automation_job_duration_seconds = Histogram(
    "automation_job_duration_seconds",
    "Duration of automation jobs in seconds",
    labelnames=["action"],
)

automation_job_queue_depth = Gauge(
    "automation_job_queue_depth",
    "Number of jobs currently in PENDING state",
)

# ----------------------------
# In-memory job store (simple)
# ----------------------------
JobStore = Dict[str, Dict[str, Any]]
jobs: JobStore = {}

VALID_ACTIONS = {"restart_service", "rotate_config", "health_check"}
STATUS_PENDING = "PENDING"
STATUS_RUNNING = "RUNNING"
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"


class CreateJobRequest(BaseModel):
    action: str = Field(..., examples=["restart_service"])
    target: str = Field(..., examples=["demo-api"])
    requested_by: str = Field(..., examples=["student@example.com"])
    parameters: Dict[str, Any] = Field(default_factory=dict)


class CreateJobResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    action: str
    target: str
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_job(job_id: str) -> None:
    job = jobs.get(job_id)
    if not job:
        return

    # Mark running
    job["status"] = STATUS_RUNNING
    job["started_at"] = now_iso()

    start = time.time()
    try:
        # Simulated work: sleep 0.3-1.5s
        time.sleep(random.uniform(0.3, 1.5))

        # Simulated failure rate (10%)
        if random.random() < 0.10:
            raise RuntimeError("simulated automation failure")

        job["status"] = STATUS_SUCCESS
        job["finished_at"] = now_iso()
        automation_jobs_total.labels(action=job["action"], status=STATUS_SUCCESS).inc()

    except Exception as e:
        job["status"] = STATUS_FAILED
        job["error"] = str(e)
        job["finished_at"] = now_iso()
        automation_jobs_total.labels(action=job["action"], status=STATUS_FAILED).inc()

    finally:
        duration = time.time() - start
        automation_job_duration_seconds.labels(action=job["action"]).observe(duration)


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/jobs", status_code=202, response_model=CreateJobResponse)
def create_job(req: CreateJobRequest, bg: BackgroundTasks) -> CreateJobResponse:
    if req.action not in VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"unsupported action: {req.action}")

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "action": req.action,
        "target": req.target,
        "requested_by": req.requested_by,
        "parameters": req.parameters,
        "status": STATUS_PENDING,
        "started_at": None,
        "finished_at": None,
        "error": None,
        "created_at": now_iso(),
    }

    # Update queue depth gauge (PENDING count)
    pending = sum(1 for j in jobs.values() if j["status"] == STATUS_PENDING)
    automation_job_queue_depth.set(pending)

    # Run async in background (non-blocking)
    bg.add_task(run_job, job_id)

    return CreateJobResponse(job_id=job_id, status=STATUS_PENDING)


@app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str) -> JobStatusResponse:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    # Keep queue depth gauge accurate
    pending = sum(1 for j in jobs.values() if j["status"] == STATUS_PENDING)
    automation_job_queue_depth.set(pending)

    return JobStatusResponse(
        job_id=job["job_id"],
        action=job["action"],
        target=job["target"],
        status=job["status"],
        started_at=job["started_at"],
        finished_at=job["finished_at"],
        error=job["error"],
    )


@app.get("/metrics")
def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@app.get("/lab/span-demo")
def span_demo(ms: int = 150, fail: bool = False):
    with tracer.start_as_current_span("business_logic") as span:
        span.set_attribute("demo.ms", ms)
        time.sleep(ms / 1000)

        with tracer.start_as_current_span("downstream_work"):
            time.sleep(0.05)

        if fail:
            raise RuntimeError("boom (intentional)")

    return {"ok": True, "slept_ms": ms, "fail": fail}


@app.get("/lab/http-child")
def http_child():
    r = httpx.get("https://example.com", timeout=5.0)
    return {"status": r.status_code}
