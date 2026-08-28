from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from worker.render import VideoRenderer


def main() -> None:
    print("[1/4] Loading Piper voice...", flush=True)
    renderer = VideoRenderer(PROJECT_ROOT / "data")

    episode = {
        "scenes": [
            {
                "heading": "What If Earth Had Rings?",
                "narration": "Imagine looking up tonight and seeing enormous rings stretching across the sky. This is a short AutoTube rendering test.",
                "points": ["A planet visual built locally", "No paid image generator"],
                "visual_type": "planet",
            },
            {
                "heading": "The Sky Changes With Latitude",
                "narration": "The rings would look dramatically different depending on your latitude, creating a completely new view of the night sky.",
                "points": ["Equator: rings cross overhead", "Higher latitudes: lower on the horizon", "Every region sees a different geometry"],
                "visual_type": "timeline",
            },
            {
                "heading": "A New Satellite Problem",
                "narration": "Satellites and spacecraft would also face a much more complicated orbital environment, changing how engineers plan missions.",
                "points": ["More orbital hazards", "Different safe paths", "Engineering tradeoffs"],
                "visual_type": "network",
            },
        ]
    }
    metadata = {
        "title": "What If Earth Had Rings?",
        "thumbnail_text": "EARTH WITH RINGS?",
    }

    job_id = f"render-test-{uuid.uuid4().hex[:8]}"
    print("[2/4] Rendering 3 varied scenes on CPU...", flush=True)
    started = time.time()
    result = renderer.render_episode(job_id, episode, metadata)
    elapsed = time.time() - started

    video = result["video_path"]
    thumb = result["thumbnail_path"]
    print("[3/4] Render complete.", flush=True)
    print("[4/4] Files ready:", flush=True)
    print(json.dumps({
        "video_path": str(video),
        "thumbnail_path": str(thumb),
        "video_mb": round(video.stat().st_size / 1024 / 1024, 2),
        "elapsed_seconds": round(elapsed, 1),
    }, indent=2))


if __name__ == "__main__":
    main()
