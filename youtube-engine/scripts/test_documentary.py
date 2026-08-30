from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from worker.documentary import DocumentaryRenderer


def latest_v3_video(data_dir: Path) -> Path | None:
    candidates = sorted(data_dir.glob("v3-bridge-test-*/final.mp4"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the private AutoTube documentary pilot")
    parser.add_argument("--source", type=Path, help="Rejected V3 video; defaults to the newest V3 bridge test")
    parser.add_argument("--narration-wav", type=Path, help="Optional existing WAV for offline visual testing")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    source = args.source or latest_v3_video(data_dir)
    if not source:
        raise SystemExit("No V3 source found. Pass --source /path/to/rejected-video.mp4")

    print("[1/4] Source locked: the rejected V3 output (evidence, not final style).", flush=True)
    print("[2/4] Rendering a build-in-public mini-documentary. Upload remains disabled.", flush=True)
    renderer = DocumentaryRenderer(data_dir)
    started = time.time()
    result = renderer.render(
        f"documentary-pilot-{uuid.uuid4().hex[:8]}",
        source.resolve(),
        args.narration_wav.resolve() if args.narration_wav else None,
    )
    elapsed = time.time() - started
    if float(result["duration"]) < 45:
        raise RuntimeError(f"Pilot is unexpectedly short: {result['duration']:.1f}s")
    print("[3/4] Private pilot passed the technical render check.", flush=True)
    print("[4/4] Review these files manually; do not upload yet:")
    print(json.dumps({
        "video_path": str(result["video_path"]),
        "thumbnail_path": str(result["thumbnail_path"]),
        "duration_seconds": round(float(result["duration"]), 1),
        "render_seconds": round(elapsed, 1),
        "format": "real evidence + documentary motion graphics + human editorial verdict",
        "youtube_upload": "DISABLED",
    }, indent=2))


if __name__ == "__main__":
    main()
