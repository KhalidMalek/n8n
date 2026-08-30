from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from worker.pipeline import Pipeline

app = FastAPI(title="AutoTube Worker", version="0.3.0")
pipeline = Pipeline()
_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _execute(job_id: str) -> None:
    with _lock:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()
    try:
        result = pipeline.run(job_id=job_id)
        with _lock:
            _jobs[job_id].update({"status": "completed", "result": result})
    except Exception as exc:  # noqa: BLE001
        with _lock:
            _jobs[job_id].update({"status": "failed", "error": str(exc)})


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "version": app.version,
        "format": "recurring-character-simulations",
        "upload_enabled": pipeline.settings.upload_enabled,
        "privacy_status": pipeline.settings.privacy_status,
    }


@app.post("/run", status_code=202)
def run_pipeline() -> dict:
    job_id = str(uuid.uuid4())
    with _lock:
        active_job = next(
            (
                existing_id
                for existing_id, job in _jobs.items()
                if job.get("status") in {"queued", "running"}
            ),
            None,
        )
        if active_job:
            raise HTTPException(
                status_code=409,
                detail=f"AutoTube is already running job {active_job}",
            )
        _jobs[job_id] = {
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    thread = threading.Thread(target=_execute, args=(job_id,), daemon=True)
    thread.start()
    return {"job_id": job_id, "status": "queued"}


@app.get("/status/{job_id}")
def job_status(job_id: str) -> dict:
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job")
    return {"job_id": job_id, **job}
