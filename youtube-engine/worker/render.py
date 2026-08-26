from __future__ import annotations

import math
import subprocess
from pathlib import Path
from textwrap import wrap
from typing import Any

import numpy as np
import soundfile as sf
from kokoro import KPipeline
from PIL import Image, ImageDraw, ImageFont


class VideoRenderer:
    WIDTH = 1920
    HEIGHT = 1080

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.font_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        self.font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        self.tts = KPipeline(lang_code="a")

    @staticmethod
    def _safe_name(value: str) -> str:
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in value)[:80]

    def _tts_to_file(self, text: str, path: Path) -> float:
        chunks: list[np.ndarray] = []
        for _, _, audio in self.tts(text, voice="af_heart", speed=1.02):
            chunks.append(np.asarray(audio, dtype=np.float32))
        if not chunks:
            raise RuntimeError("Kokoro returned no audio")
        audio = np.concatenate(chunks)
        sf.write(path, audio, 24000)
        return len(audio) / 24000.0

    def _scene_image(self, heading: str, points: list[str], index: int, total: int, path: Path) -> None:
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), (8, 12, 24))
        draw = ImageDraw.Draw(img)

        for i in range(32):
            x = (index * 173 + i * 251) % self.WIDTH
            y = (index * 97 + i * 137) % self.HEIGHT
            r = 2 + (i % 4)
            shade = 70 + (i * 7) % 100
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(shade, shade, min(255, shade + 35)))

        accent_x = 120 + ((index * 190) % 600)
        accent_y = 150 + ((index * 120) % 380)
        draw.ellipse((accent_x, accent_y, accent_x + 620, accent_y + 620), outline=(64, 140, 255), width=8)
        draw.ellipse((accent_x + 120, accent_y + 120, accent_x + 500, accent_y + 500), outline=(131, 92, 255), width=5)

        title_font = ImageFont.truetype(self.font_bold, 76)
        body_font = ImageFont.truetype(self.font_regular, 42)
        small_font = ImageFont.truetype(self.font_regular, 28)

        text_x = 920
        y = 170
        for line in wrap(heading, 24):
            draw.text((text_x, y), line, font=title_font, fill=(245, 248, 255))
            y += 92
        y += 40
        for point in points[:4]:
            lines = wrap(point, 38)
            draw.ellipse((text_x, y + 15, text_x + 14, y + 29), fill=(110, 170, 255))
            for line in lines:
                draw.text((text_x + 34, y), line, font=body_font, fill=(206, 218, 240))
                y += 56
            y += 22

        draw.text((120, 960), f"SCENE {index}/{total}", font=small_font, fill=(140, 160, 195))
        img.save(path, quality=95)

    def _make_segment(self, image: Path, audio: Path, duration: float, out: Path) -> None:
        frames = max(1, math.ceil(duration * 30))
        vf = (
            "scale=2200:1238,"
            f"zoompan=z='min(zoom+0.00035,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=30,"
            "format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", str(image), "-i", str(audio),
            "-vf", vf, "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "160k", "-shortest", str(out),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _thumbnail(self, title: str, text: str, path: Path) -> None:
        img = Image.new("RGB", (1280, 720), (7, 10, 22))
        draw = ImageDraw.Draw(img)
        for i in range(14):
            x = 50 + i * 96
            y = 80 + ((i * 137) % 510)
            draw.ellipse((x, y, x + 22, y + 22), fill=(70 + i * 8, 120, 220))
        draw.ellipse((735, 85, 1235, 585), outline=(83, 151, 255), width=18)
        draw.ellipse((835, 185, 1135, 485), outline=(170, 92, 255), width=10)

        big = ImageFont.truetype(self.font_bold, 100)
        small = ImageFont.truetype(self.font_bold, 34)
        y = 180
        for line in wrap(text.upper(), 12)[:3]:
            draw.text((65, y), line, font=big, fill=(250, 252, 255))
            y += 112
        draw.text((70, 630), title[:70], font=small, fill=(150, 170, 205))
        img.save(path, quality=94)

    def render_episode(self, job_id: str, episode: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Path]:
        run_dir = self.data_dir / self._safe_name(job_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        segments: list[Path] = []
        scenes = episode["scenes"]

        for idx, scene in enumerate(scenes, start=1):
            image = run_dir / f"scene_{idx:02d}.png"
            audio = run_dir / f"scene_{idx:02d}.wav"
            segment = run_dir / f"scene_{idx:02d}.mp4"
            self._scene_image(scene["heading"], scene.get("points", []), idx, len(scenes), image)
            duration = self._tts_to_file(scene["narration"], audio)
            self._make_segment(image, audio, duration, segment)
            segments.append(segment)

        concat = run_dir / "concat.txt"
        concat.write_text("\n".join(f"file '{p.name}'" for p in segments), encoding="utf-8")
        final_video = run_dir / "final.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(final_video)],
            check=True,
            cwd=run_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        thumbnail = run_dir / "thumbnail.jpg"
        self._thumbnail(metadata["title"], metadata.get("thumbnail_text", "WHAT IF?"), thumbnail)
        return {"video_path": final_video, "thumbnail_path": thumbnail}

    def quality_check(self, video_path: Path) -> None:
        if not video_path.exists() or video_path.stat().st_size < 1_000_000:
            raise RuntimeError("Quality gate failed: rendered video is missing or unexpectedly small")
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(video_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        duration = float(result.stdout.strip())
        if duration < 180:
            raise RuntimeError(f"Quality gate failed: video is only {duration:.0f}s; minimum V1 duration is 180s")
