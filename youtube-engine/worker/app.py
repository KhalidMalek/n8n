from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from worker.pipeline import Pipeline

app = FastAPI(title="AutoTube Worker", version="0.1.0")
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
    return {"ok": True}


@app.post("/run", status_code=202)
def run_pipeline() -> dict:
    job_id = str(uuid.uuid4())
    with _lock:
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
