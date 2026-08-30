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

from worker.render import VideoRenderer


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    episode = {
        "working_title": "Can Four Robots Cross a Collapsing Bridge?",
        "characters": ["Nova", "Mira", "Bolt", "Pix"],
        "scenes": [
            {
                "heading": "Four Robots. One Weak Bridge.",
                "narration": "Nova, Mira, Bolt and Pix have one mission: cross the canyon before the bridge collapses. The first robot to reach the far side must guide the others.",
                "points": ["Four recurring characters", "One collapsing bridge"],
                "visual_type": "simulation",
                "simulation_type": "bridge",
                "simulation_start": 0.0,
                "simulation_end": 0.20,
                "shots": [
                    {"action": "Meet the robot team", "caption": "THE TEAM LINES UP"},
                    {"action": "Reveal the canyon", "caption": "THE BRIDGE IS ALREADY CRACKING"},
                ],
            },
            {
                "heading": "The First Planks Break",
                "narration": "Nova runs first, but every step shakes the wooden planks. Behind her, the bridge begins falling away, leaving the slower robots with nowhere to stop.",
                "points": ["No turning back", "The gap keeps growing"],
                "visual_type": "simulation",
                "simulation_type": "bridge",
                "simulation_start": 0.20,
                "simulation_end": 0.46,
                "shots": [
                    {"action": "Nova accelerates", "caption": "NOVA GOES FIRST"},
                    {"action": "Planks start dropping", "caption": "THE BRIDGE BREAKS BEHIND THEM"},
                ],
            },
            {
                "heading": "No Time to Slow Down",
                "narration": "Mira and Bolt match Nova's pace while Pix falls behind. The team cannot repair the bridge, so their only option is a perfectly timed group jump.",
                "points": ["Pix is falling behind", "They need one synchronized jump"],
                "visual_type": "simulation",
                "simulation_type": "bridge",
                "simulation_start": 0.46,
                "simulation_end": 0.66,
                "shots": [
                    {"action": "The team closes formation", "caption": "PIX NEEDS HELP"},
                    {"action": "Nova signals the jump", "caption": "THREE... TWO... ONE..."},
                ],
            },
            {
                "heading": "The Final Jump",
                "narration": "All four robots launch as the last safe planks disappear. Nova lands first, Mira and Bolt follow, and Pix clears the canyon by the smallest possible margin.",
                "points": ["All four jump", "Pix barely clears the gap"],
                "visual_type": "simulation",
                "simulation_type": "bridge",
                "simulation_start": 0.66,
                "simulation_end": 0.86,
                "shots": [
                    {"action": "The bridge gives way", "caption": "THE LAST PLANK FALLS"},
                    {"action": "The team jumps", "caption": "CAN PIX MAKE IT?"},
                ],
            },
            {
                "heading": "Challenge Complete",
                "narration": "The team reaches the far side together. Their winning strategy was simple: one leader, no sudden stops, and a jump timed for the slowest member.",
                "points": ["Team safe", "Strategy beats speed"],
                "visual_type": "simulation",
                "simulation_type": "bridge",
                "simulation_start": 0.86,
                "simulation_end": 1.0,
                "shots": [
                    {"action": "Everyone reaches safety", "caption": "ALL FOUR ROBOTS SURVIVE"},
                    {"action": "Show the winning strategy", "caption": "TEAMWORK WINS"},
                ],
            },
        ],
    }
    metadata = {
        "title": "Can 4 Robots Cross a Collapsing Bridge?",
        "thumbnail_text": "BRIDGE BREAKS!",
    }

    job_id = f"v3-bridge-test-{uuid.uuid4().hex[:8]}"
    print("[1/4] Loading the local Piper voice and V3 simulation engine...", flush=True)
    renderer = VideoRenderer(data_dir)
    print("[2/4] Rendering the recurring-character bridge challenge...", flush=True)
    started = time.time()
    result = renderer.render_episode(job_id, episode, metadata)
    elapsed = time.time() - started
    renderer.quality_check(result["video_path"], min_duration=45)
    print("[3/4] V3 quality gate passed.", flush=True)
    payload = {
        "video_path": str(result["video_path"]),
        "thumbnail_path": str(result["thumbnail_path"]),
        "video_mb": round(result["video_path"].stat().st_size / 1024 / 1024, 2),
        "elapsed_seconds": round(elapsed, 1),
        "format": "original recurring characters + frame-by-frame simulation",
    }
    print("[4/4] Files ready:")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
