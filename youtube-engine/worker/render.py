from __future__ import annotations

import math
import os
import random
import subprocess
import wave
from pathlib import Path
from textwrap import wrap
from typing import Any

from piper import PiperVoice
from PIL import Image, ImageDraw, ImageFont, ImageFilter


class VideoRenderer:
    WIDTH = 1920
    HEIGHT = 1080
    FPS = 24

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.font_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        self.font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        model_path = Path(os.getenv("PIPER_MODEL", "voices/en_US-ljspeech-medium.onnx"))
        if not model_path.is_absolute():
            model_path = Path.cwd() / model_path
        if not model_path.exists():
            raise RuntimeError(
                f"Piper voice model is missing: {model_path}. "
                "Run: python -m piper.download_voices --data-dir voices en_US-ljspeech-medium"
            )
        self.tts = PiperVoice.load(str(model_path))

    @staticmethod
    def _safe_name(value: str) -> str:
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in value)[:80]

    def _font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(self.font_bold if bold else self.font_regular, size)

    def _tts_to_file(self, text: str, path: Path) -> float:
        with wave.open(str(path), "wb") as wav_file:
            self.tts.synthesize_wav(text, wav_file)
        with wave.open(str(path), "rb") as wav_file:
            frame_rate = wav_file.getframerate()
            frames = wav_file.getnframes()
        if frame_rate <= 0 or frames <= 0:
            raise RuntimeError("Piper returned empty audio")
        return frames / frame_rate

    def _gradient_background(self, seed: int) -> Image.Image:
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), (7, 11, 24))
        px = img.load()
        for y in range(self.HEIGHT):
            t = y / max(1, self.HEIGHT - 1)
            r = int(6 + 8 * t)
            g = int(10 + 8 * t)
            b = int(24 + 20 * t)
            for x in range(self.WIDTH):
                px[x, y] = (r, g, b)
        draw = ImageDraw.Draw(img)
        rng = random.Random(seed)
        for _ in range(80):
            x = rng.randrange(20, self.WIDTH - 20)
            y = rng.randrange(20, self.HEIGHT - 20)
            r = rng.choice([1, 2, 2, 3])
            shade = rng.randrange(105, 210)
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(shade, shade, min(255, shade + 30)))
        return img

    @staticmethod
    def _scene_type(scene: dict[str, Any]) -> str:
        explicit = str(scene.get("visual_type", "")).strip().lower()
        allowed = {"planet", "network", "city", "chart", "timeline", "comparison", "energy", "generic"}
        if explicit in allowed:
            return explicit
        text = f"{scene.get('heading','')} {' '.join(scene.get('points', []))}".lower()
        if any(k in text for k in ("earth", "moon", "planet", "mars", "space", "orbit", "ring", "sun", "asteroid")):
            return "planet"
        if any(k in text for k in ("ai", "neural", "network", "computer", "data", "internet", "robot")):
            return "network"
        if any(k in text for k in ("city", "traffic", "building", "urban", "street")):
            return "city"
        if any(k in text for k in ("percent", "growth", "increase", "decrease", "chart", "rate", "billion", "million")):
            return "chart"
        if any(k in text for k in ("year", "timeline", "first", "next", "future", "history")):
            return "timeline"
        if any(k in text for k in ("versus", " vs ", "compare", "before", "after")):
            return "comparison"
        if any(k in text for k in ("energy", "power", "electric", "solar", "fusion")):
            return "energy"
        return "generic"

    def _text_block(
        self,
        draw: ImageDraw.ImageDraw,
        heading: str,
        points: list[str],
        x: int,
        y: int,
        width_chars: int = 24,
        heading_size: int = 70,
        body_size: int = 36,
    ) -> None:
        title_font = self._font(heading_size, bold=True)
        body_font = self._font(body_size)
        for line in wrap(heading, width_chars)[:3]:
            draw.text((x, y), line, font=title_font, fill=(248, 250, 255))
            y += heading_size + 16
        y += 26
        for point in points[:3]:
            draw.ellipse((x, y + 15, x + 12, y + 27), fill=(94, 166, 255))
            for line in wrap(point, 38)[:2]:
                draw.text((x + 28, y), line, font=body_font, fill=(204, 216, 237))
                y += body_size + 14
            y += 18

    def _draw_planet(self, img: Image.Image, scene: dict[str, Any], seed: int) -> None:
        draw = ImageDraw.Draw(img, "RGBA")
        cx, cy = 560, 520
        radius = 260

        glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow, "RGBA")
        for r in range(radius + 85, radius, -12):
            alpha = max(6, int(70 * (radius + 85 - r) / 85))
            gd.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(40, 115, 255, alpha))
        glow = glow.filter(ImageFilter.GaussianBlur(28))
        img.paste(glow, (0, 0), glow)

        draw = ImageDraw.Draw(img, "RGBA")
        draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=(26, 103, 197, 255))
        draw.pieslice((cx-radius+35, cy-radius+25, cx+radius-25, cy+radius-20), 190, 350, fill=(27, 152, 120, 150))
        draw.ellipse((cx-radius+40, cy-radius+55, cx+radius-30, cy+radius-35), outline=(132, 215, 255, 110), width=10)

        text = f"{scene.get('heading','')} {' '.join(scene.get('points', []))}".lower()
        if "ring" in text or "saturn" in text:
            ring_box = (cx-radius-140, cy-105, cx+radius+140, cy+105)
            draw.ellipse(ring_box, outline=(116, 184, 255, 220), width=28)
            inner = (cx-radius-70, cy-55, cx+radius+70, cy+55)
            draw.ellipse(inner, outline=(177, 102, 255, 190), width=12)

        self._text_block(draw, scene.get("heading", ""), scene.get("points", []), 960, 170, 23)

    def _draw_network(self, img: Image.Image, scene: dict[str, Any], seed: int) -> None:
        draw = ImageDraw.Draw(img, "RGBA")
        rng = random.Random(seed)
        nodes = []
        for _ in range(24):
            nodes.append((rng.randrange(110, 1120), rng.randrange(190, 900)))
        for i, (x, y) in enumerate(nodes):
            for j in range(i + 1, len(nodes)):
                x2, y2 = nodes[j]
                d2 = (x-x2) ** 2 + (y-y2) ** 2
                if d2 < 105000 and rng.random() < 0.42:
                    draw.line((x, y, x2, y2), fill=(64, 132, 240, 80), width=3)
        for i, (x, y) in enumerate(nodes):
            rr = 8 + (i % 4) * 3
            fill = (70, 165, 255, 230) if i % 3 else (176, 93, 255, 240)
            draw.ellipse((x-rr, y-rr, x+rr, y+rr), fill=fill)
        draw.rounded_rectangle((110, 120, 1150, 930), radius=42, outline=(74, 136, 232, 100), width=4)
        self._text_block(draw, scene.get("heading", ""), scene.get("points", []), 1240, 180, 20)

    def _draw_city(self, img: Image.Image, scene: dict[str, Any], seed: int) -> None:
        draw = ImageDraw.Draw(img, "RGBA")
        rng = random.Random(seed)
        x = 60
        while x < 1260:
            w = rng.randrange(80, 150)
            h = rng.randrange(230, 650)
            top = 940 - h
            draw.rectangle((x, top, x+w, 940), fill=(18, 31, 58, 255), outline=(58, 96, 155, 180), width=3)
            for wx in range(x+18, x+w-10, 28):
                for wy in range(top+30, 910, 42):
                    if rng.random() < 0.45:
                        draw.rectangle((wx, wy, wx+9, wy+13), fill=(255, 205, 91, 160))
            x += w + rng.randrange(15, 40)
        draw.line((60, 955, 1260, 955), fill=(87, 159, 255, 180), width=5)
        self._text_block(draw, scene.get("heading", ""), scene.get("points", []), 1330, 150, 18, 62, 32)

    def _draw_chart(self, img: Image.Image, scene: dict[str, Any], seed: int) -> None:
        draw = ImageDraw.Draw(img, "RGBA")
        left, top, right, bottom = 120, 250, 1180, 880
        draw.line((left, bottom, right, bottom), fill=(140, 164, 205, 170), width=4)
        draw.line((left, top, left, bottom), fill=(140, 164, 205, 170), width=4)
        rng = random.Random(seed)
        values = [rng.randrange(30, 80)]
        for _ in range(5):
            values.append(max(18, min(100, values[-1] + rng.randrange(-10, 26))))
        step = (right-left-80) // len(values)
        pts = []
        for i, v in enumerate(values):
            x = left + 60 + i * step
            y = bottom - int((bottom-top-80) * v / 100)
            pts.append((x, y))
            draw.ellipse((x-10, y-10, x+10, y+10), fill=(98, 171, 255, 255))
        draw.line(pts, fill=(98, 171, 255, 255), width=10, joint="curve")
        self._text_block(draw, scene.get("heading", ""), scene.get("points", []), 1300, 170, 18, 60, 32)

    def _draw_timeline(self, img: Image.Image, scene: dict[str, Any], seed: int) -> None:
        draw = ImageDraw.Draw(img, "RGBA")
        y = 610
        draw.line((140, y, 1260, y), fill=(84, 151, 255, 200), width=8)
        labels = scene.get("points", [])[:4] or ["Now", "Next", "Later"]
        count = len(labels)
        for i, label in enumerate(labels):
            x = 180 + int(i * (1020 / max(1, count-1))) if count > 1 else 700
            draw.ellipse((x-25, y-25, x+25, y+25), fill=(175, 94, 255, 255), outline=(220, 205, 255, 255), width=4)
            for li, line in enumerate(wrap(label, 18)[:2]):
                draw.text((x-85, y+55+li*34), line, font=self._font(28), fill=(205, 218, 240))
        draw.text((140, 150), scene.get("heading", ""), font=self._font(72, True), fill=(248, 250, 255))

    def _draw_comparison(self, img: Image.Image, scene: dict[str, Any], seed: int) -> None:
        draw = ImageDraw.Draw(img, "RGBA")
        draw.rounded_rectangle((90, 250, 890, 900), radius=50, fill=(18, 37, 72, 210), outline=(84, 151, 255, 180), width=5)
        draw.rounded_rectangle((1030, 250, 1830, 900), radius=50, fill=(42, 24, 72, 210), outline=(175, 94, 255, 180), width=5)
        draw.text((90, 110), scene.get("heading", ""), font=self._font(68, True), fill=(248, 250, 255))
        points = scene.get("points", [])
        halves = [points[::2], points[1::2]]
        for side, items in enumerate(halves):
            x = 150 if side == 0 else 1090
            y = 360
            for item in items[:3]:
                for line in wrap(item, 28)[:2]:
                    draw.text((x, y), line, font=self._font(34), fill=(214, 226, 245))
                    y += 48
                y += 42

    def _draw_energy(self, img: Image.Image, scene: dict[str, Any], seed: int) -> None:
        draw = ImageDraw.Draw(img, "RGBA")
        cx, cy = 610, 555
        for r, a in ((320, 35), (250, 60), (185, 100)):
            draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline=(255, 188, 65, a), width=12)
        bolt = [(575, 250), (445, 585), (585, 585), (505, 875), (790, 480), (635, 480)]
        draw.polygon(bolt, fill=(255, 207, 73, 240))
        self._text_block(draw, scene.get("heading", ""), scene.get("points", []), 1040, 170, 22)

    def _draw_generic(self, img: Image.Image, scene: dict[str, Any], seed: int) -> None:
        draw = ImageDraw.Draw(img, "RGBA")
        for i in range(8):
            x = 120 + i * 130
            y = 310 + int(150 * math.sin(i * 0.8))
            size = 95 + (i % 3) * 35
            draw.rounded_rectangle((x, y, x+size, y+size), radius=24, fill=(35, 66, 118, 190), outline=(95, 165, 255, 160), width=4)
            if i:
                px = 120 + (i-1) * 130 + 60
                py = 310 + int(150 * math.sin((i-1) * 0.8)) + 60
                draw.line((px, py, x, y+size//2), fill=(121, 96, 255, 130), width=5)
        self._text_block(draw, scene.get("heading", ""), scene.get("points", []), 1170, 160, 20, 62, 32)

    def _scene_image(self, scene: dict[str, Any], index: int, total: int, path: Path) -> None:
        scene_type = self._scene_type(scene)
        img = self._gradient_background(index * 9973 + total)
        if scene_type == "planet":
            self._draw_planet(img, scene, index)
        elif scene_type == "network":
            self._draw_network(img, scene, index)
        elif scene_type == "city":
            self._draw_city(img, scene, index)
        elif scene_type == "chart":
            self._draw_chart(img, scene, index)
        elif scene_type == "timeline":
            self._draw_timeline(img, scene, index)
        elif scene_type == "comparison":
            self._draw_comparison(img, scene, index)
        elif scene_type == "energy":
            self._draw_energy(img, scene, index)
        else:
            self._draw_generic(img, scene, index)

        draw = ImageDraw.Draw(img, "RGBA")
        draw.rounded_rectangle((80, 965, 330, 1025), radius=18, fill=(6, 10, 22, 180))
        draw.text((105, 980), f"{index:02d} / {total:02d}  •  {scene_type.upper()}", font=self._font(24), fill=(145, 167, 205))
        img.save(path, quality=95)

    def _make_segment(self, image: Path, audio: Path, duration: float, out: Path) -> None:
        frames = max(1, math.ceil(duration * self.FPS))
        vf = (
            "scale=2048:1152,"
            f"zoompan=z='min(zoom+0.00045,1.07)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={self.FPS},"
            "format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", str(image), "-i", str(audio),
            "-vf", vf, "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "ultrafast",
            "-crf", "22", "-c:a", "aac", "-b:a", "128k", "-shortest", str(out),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _thumbnail(self, title: str, text: str, path: Path) -> None:
        scene = {"heading": title, "points": [], "visual_type": self._scene_type({"heading": title, "points": []})}
        img = self._gradient_background(777)
        scene_type = scene["visual_type"]
        if scene_type == "planet":
            self._draw_planet(img, {"heading": "", "points": [], "visual_type": "planet"}, 1)
        elif scene_type == "network":
            self._draw_network(img, {"heading": "", "points": [], "visual_type": "network"}, 2)
        elif scene_type == "city":
            self._draw_city(img, {"heading": "", "points": [], "visual_type": "city"}, 3)
        elif scene_type == "energy":
            self._draw_energy(img, {"heading": "", "points": [], "visual_type": "energy"}, 4)
        else:
            self._draw_generic(img, {"heading": "", "points": [], "visual_type": "generic"}, 5)

        img = img.resize((1280, 720))
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay, "RGBA")
        od.rectangle((0, 0, 650, 720), fill=(3, 7, 18, 160))
        overlay = overlay.filter(ImageFilter.GaussianBlur(2))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        big = ImageFont.truetype(self.font_bold, 94)
        y = 170
        for line in wrap(text.upper(), 11)[:3]:
            draw.text((62, y+5), line, font=big, fill=(0, 0, 0))
            draw.text((56, y), line, font=big, fill=(255, 255, 255))
            y += 105
        draw.rounded_rectangle((56, 590, 250, 638), radius=14, fill=(78, 143, 255))
        draw.text((78, 600), "WHAT IF?", font=ImageFont.truetype(self.font_bold, 25), fill=(255, 255, 255))
        img.save(path, quality=95)

    def render_episode(self, job_id: str, episode: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Path]:
        run_dir = self.data_dir / self._safe_name(job_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        segments: list[Path] = []
        scenes = episode["scenes"]

        for idx, scene in enumerate(scenes, start=1):
            scene_type = self._scene_type(scene)
            print(f"  [render] Scene {idx}/{len(scenes)} • {scene_type}: generating voice...", flush=True)
            image = run_dir / f"scene_{idx:02d}.png"
            audio = run_dir / f"scene_{idx:02d}.wav"
            segment = run_dir / f"scene_{idx:02d}.mp4"
            duration = self._tts_to_file(scene["narration"], audio)
            print(f"  [render] Scene {idx}/{len(scenes)} • {duration:.1f}s: building visual + encoding...", flush=True)
            self._scene_image(scene, idx, len(scenes), image)
            self._make_segment(image, audio, duration, segment)
            segments.append(segment)

        print("  [render] Joining scenes...", flush=True)
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

        print("  [render] Creating thumbnail...", flush=True)
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
