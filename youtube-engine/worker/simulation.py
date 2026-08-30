from __future__ import annotations

import math
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap
from typing import Any

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class CharacterSpec:
    name: str
    body: tuple[int, int, int]
    accent: tuple[int, int, int]
    eye: tuple[int, int, int]


CAST = (
    CharacterSpec("NOVA", (48, 173, 255), (224, 248, 255), (10, 34, 56)),
    CharacterSpec("MIRA", (167, 99, 255), (244, 225, 255), (37, 17, 61)),
    CharacterSpec("BOLT", (255, 151, 57), (255, 236, 187), (67, 31, 7)),
    CharacterSpec("PIX", (53, 210, 151), (211, 255, 235), (8, 50, 34)),
)


class SimulationRenderer:
    """Small CPU-only animation engine for AutoTube's recurring robot cast."""

    WIDTH = 1280
    HEIGHT = 720
    OUTPUT_WIDTH = 1920
    OUTPUT_HEIGHT = 1080
    FPS = 24

    def __init__(self, font_regular: str, font_bold: str) -> None:
        self.font_regular = font_regular
        self.font_bold = font_bold

    def _font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(self.font_bold if bold else self.font_regular, size)

    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

    @classmethod
    def _smoothstep(cls, value: float) -> float:
        value = cls._clamp(value)
        return value * value * (3.0 - 2.0 * value)

    @staticmethod
    def _caption_chunks(text: str, words_per_chunk: int = 7) -> list[str]:
        words = text.replace("\n", " ").split()
        if not words:
            return []
        return [" ".join(words[i : i + words_per_chunk]) for i in range(0, len(words), words_per_chunk)]

    @staticmethod
    def _active_shot(scene: dict[str, Any], progress: float) -> tuple[dict[str, Any], float, int, int]:
        raw_shots = scene.get("shots")
        shots = [shot for shot in raw_shots if isinstance(shot, dict)] if isinstance(raw_shots, list) else []
        if not shots:
            shots = [
                {
                    "action": scene.get("heading", "Simulation"),
                    "caption": scene.get("heading", "Simulation"),
                }
            ]
        count = len(shots)
        scaled = min(progress, 0.999999) * count
        index = min(count - 1, int(scaled))
        return shots[index], scaled - index, index, count

    def _draw_stars(self, draw: ImageDraw.ImageDraw, seed: int, drift: float = 0.0) -> None:
        rng = random.Random(seed)
        for _ in range(75):
            x = (rng.randrange(0, self.WIDTH) + int(drift)) % self.WIDTH
            y = rng.randrange(30, 500)
            radius = rng.choice((1, 1, 2, 2, 3))
            shade = rng.randrange(120, 235)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(shade, shade, 255))

    def _draw_character(
        self,
        draw: ImageDraw.ImageDraw,
        spec: CharacterSpec,
        x: float,
        y: float,
        scale: float = 1.0,
        pose: str = "run",
        facing: int = 1,
        label: bool = False,
        shadow: bool = True,
    ) -> None:
        x_i, y_i = int(x), int(y)
        body_w = int(72 * scale)
        body_h = int(86 * scale)
        head_r = int(38 * scale)
        limb = int(42 * scale)
        width = max(2, int(12 * scale))

        if shadow:
            draw.ellipse(
                (x_i - int(47 * scale), y_i + int(58 * scale), x_i + int(47 * scale), y_i + int(75 * scale)),
                fill=(4, 8, 18, 90),
            )

        phase = (x_i / 45.0) % (math.pi * 2.0)
        swing = math.sin(phase) * limb * 0.55 if pose == "run" else 0
        if pose == "jump":
            swing = limb * 0.55
        arm_y = y_i - int(4 * scale)
        draw.line(
            (x_i - body_w // 2, arm_y, x_i - body_w // 2 - int(facing * swing), arm_y + limb),
            fill=spec.accent,
            width=width,
        )
        draw.line(
            (x_i + body_w // 2, arm_y, x_i + body_w // 2 + int(facing * swing), arm_y - limb),
            fill=spec.accent,
            width=width,
        )

        leg_swing = -swing if pose == "run" else int(12 * scale)
        draw.line(
            (x_i - int(18 * scale), y_i + body_h // 2, x_i - int(22 * scale) + int(leg_swing), y_i + body_h // 2 + limb),
            fill=spec.accent,
            width=width,
        )
        draw.line(
            (x_i + int(18 * scale), y_i + body_h // 2, x_i + int(22 * scale) - int(leg_swing), y_i + body_h // 2 + limb),
            fill=spec.accent,
            width=width,
        )

        draw.rounded_rectangle(
            (x_i - body_w // 2, y_i - body_h // 2, x_i + body_w // 2, y_i + body_h // 2),
            radius=max(8, int(18 * scale)),
            fill=spec.body,
            outline=spec.accent,
            width=max(2, int(4 * scale)),
        )
        draw.ellipse(
            (x_i - head_r, y_i - body_h // 2 - head_r - int(8 * scale), x_i + head_r, y_i - body_h // 2 + head_r - int(8 * scale)),
            fill=spec.accent,
            outline=(255, 255, 255),
            width=max(2, int(3 * scale)),
        )
        visor_y = y_i - body_h // 2 - int(9 * scale)
        draw.rounded_rectangle(
            (x_i - int(27 * scale), visor_y - int(13 * scale), x_i + int(27 * scale), visor_y + int(13 * scale)),
            radius=max(4, int(9 * scale)),
            fill=spec.eye,
        )
        eye_x = x_i + facing * int(11 * scale)
        draw.ellipse(
            (eye_x - int(5 * scale), visor_y - int(5 * scale), eye_x + int(5 * scale), visor_y + int(5 * scale)),
            fill=(255, 255, 255),
        )
        draw.ellipse(
            (x_i - int(11 * scale), y_i - int(9 * scale), x_i + int(11 * scale), y_i + int(13 * scale)),
            fill=spec.accent,
        )

        if label:
            font = self._font(max(14, int(18 * scale)), bold=True)
            box = draw.textbbox((0, 0), spec.name, font=font)
            text_w = box[2] - box[0]
            draw.rounded_rectangle(
                (x_i - text_w // 2 - 9, y_i - int(122 * scale), x_i + text_w // 2 + 9, y_i - int(94 * scale)),
                radius=8,
                fill=(6, 13, 28, 210),
            )
            draw.text((x_i - text_w // 2, y_i - int(120 * scale)), spec.name, font=font, fill=spec.accent)

    def _draw_bridge(self, draw: ImageDraw.ImageDraw, progress: float, shot_index: int) -> None:
        sky = (20, 31, 66)
        draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), fill=sky)
        self._draw_stars(draw, 991, drift=-progress * 45)
        draw.ellipse((1020, 70, 1160, 210), fill=(246, 212, 125))
        draw.polygon(((0, 500), (265, 300), (405, 515), (0, 650)), fill=(48, 38, 63))
        draw.polygon(((1280, 500), (1015, 300), (875, 515), (1280, 650)), fill=(48, 38, 63))
        draw.rectangle((0, 590, self.WIDTH, self.HEIGHT), fill=(7, 11, 24))

        left, right, bridge_y = 190, 1090, 455
        plank_count = 15
        plank_w = (right - left) / plank_count
        collapse = self._smoothstep((progress - 0.36) / 0.42)
        for idx in range(plank_count):
            x0 = left + idx * plank_w
            x1 = x0 + plank_w - 5
            trigger = idx / plank_count
            fall = self._smoothstep((collapse - trigger * 0.66) / 0.34)
            y_off = fall * fall * 235
            tilt = fall * 14 * (-1 if idx % 2 else 1)
            draw.polygon(
                (
                    (x0, bridge_y + y_off - tilt),
                    (x1, bridge_y + y_off + tilt),
                    (x1, bridge_y + 26 + y_off + tilt),
                    (x0, bridge_y + 26 + y_off - tilt),
                ),
                fill=(150, 99, 62),
                outline=(223, 172, 111),
            )
        draw.arc((left - 30, 250, right + 30, 660), 195, 345, fill=(197, 159, 111), width=6)
        draw.arc((left - 30, 275, right + 30, 685), 195, 345, fill=(197, 159, 111), width=4)

        team_progress = self._smoothstep(progress / 0.86)
        for idx, spec in enumerate(CAST):
            delayed = self._clamp(team_progress * 1.12 - idx * 0.035)
            start_x = 110 + idx * 78
            end_x = 1030 - idx * 70
            x = start_x + (end_x - start_x) * delayed
            jump_window = self._clamp((progress - 0.42 - idx * 0.015) / 0.26)
            jump_y = math.sin(jump_window * math.pi) * (135 if 0 < jump_window < 1 else 0)
            y = bridge_y - 67 - jump_y + math.sin(progress * 48 + idx) * 4
            pose = "jump" if jump_y > 12 else "run"
            self._draw_character(draw, spec, x, y, scale=0.72, pose=pose, label=shot_index == 0)

        if progress > 0.72:
            safe = self._smoothstep((progress - 0.72) / 0.18)
            draw.rounded_rectangle((960, 118, 1210, 190), radius=20, fill=(16, 68, 58, int(225 * safe)))
            draw.text((990, 132), "TEAM SAFE!", font=self._font(34, True), fill=(127, 255, 203))

    def _draw_gravity(self, draw: ImageDraw.ImageDraw, progress: float, shot_index: int) -> None:
        draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), fill=(18, 28, 52))
        for x in range(0, self.WIDTH, 160):
            draw.line((x, 90, x, 650), fill=(37, 59, 91), width=2)
        for y in range(90, 651, 112):
            draw.line((0, y, self.WIDTH, y), fill=(37, 59, 91), width=2)
        draw.rectangle((0, 610, self.WIDTH, self.HEIGHT), fill=(29, 40, 62))
        draw.text((62, 105), "GRAVITY LAB", font=self._font(36, True), fill=(117, 192, 255))
        for idx, spec in enumerate(CAST):
            x = 250 + idx * 255 + math.sin(progress * 7 + idx) * 45
            lift = self._smoothstep((progress - 0.12) / 0.45)
            y = 525 - lift * (210 + idx * 26) + math.sin(progress * 12 + idx * 1.7) * 50
            self._draw_character(draw, spec, x, y, scale=0.82, pose="jump", label=shot_index == 0, shadow=lift < 0.2)
        arrow_h = int(170 * self._smoothstep(progress / 0.35))
        draw.line((1120, 520, 1120, 520 - arrow_h), fill=(255, 210, 77), width=10)
        draw.polygon(((1100, 365), (1140, 365), (1120, 330)), fill=(255, 210, 77))

    def _draw_maze(self, draw: ImageDraw.ImageDraw, progress: float, shot_index: int) -> None:
        draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), fill=(9, 15, 31))
        left, top, cell = 105, 115, 72
        cols, rows = 15, 7
        rng = random.Random(384)
        for row in range(rows):
            for col in range(cols):
                if (row + col) % 4 == 0 or rng.random() < 0.17:
                    x, y = left + col * cell, top + row * cell
                    draw.rounded_rectangle((x, y, x + cell - 9, y + cell - 9), radius=10, fill=(31, 54, 91))
        path = [(125, 580), (270, 580), (270, 420), (505, 420), (505, 205), (755, 205), (755, 505), (1040, 505), (1145, 270)]
        draw.line(path, fill=(80, 157, 245), width=9, joint="curve")
        distances: list[float] = []
        total = 0.0
        for a, b in zip(path, path[1:]):
            total += math.dist(a, b)
            distances.append(total)
        for idx, spec in enumerate(CAST):
            target = self._clamp(progress * 1.12 - idx * 0.055) * total
            prev = path[0]
            cumulative = 0.0
            pos = prev
            for nxt in path[1:]:
                seg = math.dist(prev, nxt)
                if cumulative + seg >= target:
                    ratio = (target - cumulative) / max(seg, 1.0)
                    pos = (prev[0] + (nxt[0] - prev[0]) * ratio, prev[1] + (nxt[1] - prev[1]) * ratio)
                    break
                cumulative += seg
                prev = nxt
                pos = nxt
            self._draw_character(draw, spec, pos[0], pos[1], scale=0.42, pose="run", label=shot_index == 0)
        draw.rounded_rectangle((1068, 176, 1222, 257), radius=20, fill=(31, 116, 83), outline=(121, 255, 199), width=4)
        draw.text((1092, 198), "EXIT", font=self._font(30, True), fill=(219, 255, 239))

    def _draw_mars(self, draw: ImageDraw.ImageDraw, progress: float, shot_index: int) -> None:
        draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), fill=(54, 28, 41))
        draw.ellipse((1010, 75, 1140, 205), fill=(247, 193, 118))
        draw.polygon(((0, 515), (215, 310), (405, 520), (650, 335), (905, 530), (1090, 380), (1280, 525)), fill=(111, 57, 48))
        draw.rectangle((0, 515, self.WIDTH, self.HEIGHT), fill=(91, 45, 41))
        rng = random.Random(428)
        for _ in range(95):
            x = (rng.randrange(0, self.WIDTH) - int(progress * 430)) % self.WIDTH
            y = rng.randrange(250, 680)
            draw.line((x, y, x + 26, y - 5), fill=(214, 132, 91), width=2)
        for idx, spec in enumerate(CAST):
            x = 170 + idx * 245 + progress * 170
            y = 505 + math.sin(progress * 35 + idx) * 9
            self._draw_character(draw, spec, x, y, scale=0.72, pose="run", label=shot_index == 0)
        draw.rounded_rectangle((65, 85, 305, 142), radius=14, fill=(60, 24, 35, 220))
        draw.text((90, 97), "MARS: SOL 01", font=self._font(27, True), fill=(255, 189, 145))

    def _draw_simulation(self, draw: ImageDraw.ImageDraw, scene: dict[str, Any], progress: float, shot_index: int) -> None:
        scenario = str(scene.get("simulation_type", "bridge")).strip().lower()
        if scenario == "gravity":
            self._draw_gravity(draw, progress, shot_index)
        elif scenario == "maze":
            self._draw_maze(draw, progress, shot_index)
        elif scenario == "mars":
            self._draw_mars(draw, progress, shot_index)
        else:
            self._draw_bridge(draw, progress, shot_index)

    def _draw_ui(
        self,
        draw: ImageDraw.ImageDraw,
        scene: dict[str, Any],
        progress: float,
        shot: dict[str, Any],
        shot_index: int,
        shot_count: int,
    ) -> None:
        draw.rounded_rectangle((36, 30, 850, 102), radius=22, fill=(4, 9, 22, 205))
        heading = str(scene.get("heading", "AutoTube Simulation"))
        draw.text((62, 46), heading[:52], font=self._font(35, True), fill=(248, 251, 255))

        action = str(shot.get("caption") or shot.get("action") or "Challenge in progress")
        action_font = self._font(31, True)
        action_lines = wrap(action.upper(), 34)[:2]
        action_h = 58 + len(action_lines) * 39
        draw.rounded_rectangle((52, 118, 520, 118 + action_h), radius=18, fill=(10, 24, 50, 205), outline=(69, 151, 245), width=3)
        for idx, line in enumerate(action_lines):
            draw.text((78, 142 + idx * 39), line, font=action_font, fill=(135, 211, 255))
        draw.text((78, 126 + len(action_lines) * 39 + 10), f"SHOT {shot_index + 1}/{shot_count}", font=self._font(17, True), fill=(157, 173, 204))

        chunks = self._caption_chunks(str(scene.get("narration", "")))
        if chunks:
            caption_index = min(len(chunks) - 1, int(progress * len(chunks)))
            caption = chunks[caption_index]
            font = self._font(35, True)
            box = draw.textbbox((0, 0), caption, font=font)
            text_w = min(self.WIDTH - 160, box[2] - box[0])
            x = (self.WIDTH - text_w) // 2
            draw.rounded_rectangle((x - 24, 627, x + text_w + 24, 687), radius=17, fill=(2, 6, 16, 218))
            draw.text((x, 639), caption, font=font, fill=(255, 255, 255))

        bar_left, bar_right, bar_y = 910, 1235, 72
        draw.rounded_rectangle((bar_left, bar_y, bar_right, bar_y + 18), radius=9, fill=(29, 43, 69))
        fill_right = bar_left + int((bar_right - bar_left) * progress)
        draw.rounded_rectangle((bar_left, bar_y, max(bar_left + 18, fill_right), bar_y + 18), radius=9, fill=(74, 171, 255))

    def frame(self, scene: dict[str, Any], progress: float) -> Image.Image:
        progress = self._clamp(progress)
        shot, _shot_progress, shot_index, shot_count = self._active_shot(scene, progress)
        simulation_start = self._clamp(float(scene.get("simulation_start", 0.0)))
        simulation_end = self._clamp(float(scene.get("simulation_end", 1.0)))
        if simulation_end < simulation_start:
            simulation_start, simulation_end = simulation_end, simulation_start
        simulation_progress = simulation_start + progress * (simulation_end - simulation_start)
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), (7, 11, 24))
        draw = ImageDraw.Draw(img, "RGBA")
        self._draw_simulation(draw, scene, simulation_progress, shot_index)
        self._draw_ui(draw, scene, progress, shot, shot_index, shot_count)

        fade = min(self._clamp(progress / 0.018), self._clamp((1.0 - progress) / 0.018))
        if fade < 1.0:
            draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), fill=(0, 0, 0, int(255 * (1.0 - fade))))
        return img

    def render(self, scene: dict[str, Any], audio_path: Path, duration: float, output_path: Path) -> None:
        frame_count = max(1, math.ceil(duration * self.FPS))
        cmd = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{self.WIDTH}x{self.HEIGHT}",
            "-r",
            str(self.FPS),
            "-i",
            "-",
            "-i",
            str(audio_path),
            "-vf",
            f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}:flags=lanczos,format=yuv420p",
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "22",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            str(output_path),
        ]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        assert process.stdin is not None
        try:
            for frame_index in range(frame_count):
                progress = frame_index / max(1, frame_count - 1)
                process.stdin.write(self.frame(scene, progress).tobytes())
        except BrokenPipeError as exc:
            stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
            raise RuntimeError(f"FFmpeg stopped while rendering a simulation: {stderr[-2000:]}") from exc
        finally:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"FFmpeg simulation render failed ({return_code}): {stderr[-2000:]}")

    def thumbnail(self, scene: dict[str, Any], text: str, path: Path) -> None:
        thumb_scene = dict(scene)
        thumb_scene["narration"] = ""
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), (7, 11, 24))
        base_draw = ImageDraw.Draw(img, "RGBA")
        self._draw_simulation(base_draw, thumb_scene, 0.57, 1)
        img = img.resize((1280, 720))
        draw = ImageDraw.Draw(img, "RGBA")
        draw.rectangle((0, 0, 600, 720), fill=(3, 7, 17, 188))
        draw.polygon(((600, 0), (720, 0), (600, 720), (490, 720)), fill=(3, 7, 17, 120))
        font = ImageFont.truetype(self.font_bold, 92)
        y = 150
        for line in wrap(text.upper(), 11)[:3]:
            draw.text((64, y + 6), line, font=font, fill=(0, 0, 0))
            draw.text((58, y), line, font=font, fill=(255, 255, 255))
            y += 105
        draw.rounded_rectangle((62, 560, 405, 616), radius=16, fill=(51, 173, 255))
        draw.text((88, 573), "ROBOT CHALLENGE", font=ImageFont.truetype(self.font_bold, 24), fill=(3, 18, 32))
        img.save(path, quality=95)
