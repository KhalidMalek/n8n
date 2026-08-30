from __future__ import annotations

import base64
import json
import os
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


@dataclass(frozen=True)
class DocumentaryScene:
    eyebrow: str
    title: str
    narration: str
    mode: str
    points: tuple[str, ...] = ()
    source_offset: float = 0.0


PILOT_SCENES = (
    DocumentaryScene(
        "THE EXPERIMENT",
        "I BUILT A ₹0 AI\nYOUTUBE SYSTEM",
        "I built a complete AI system that can research a topic, write a script, create a voice, render a video, and prepare it for YouTube, without a GPU.",
        "hook",
        source_offset=1.5,
    ),
    DocumentaryScene(
        "THE RECEIPTS",
        "TECHNICALLY,\nIT WORKED.",
        "On a tiny two-core server with one gigabyte of memory, the first test rendered in three minutes and twenty-two seconds. Technically, everything worked.",
        "metrics",
        ("46.5 SECOND VIDEO", "1920 x 1080", "15.09 MB", "3m 22s RENDER"),
    ),
    DocumentaryScene(
        "THEN I WATCHED IT",
        "THE OUTPUT\nFELT AUTOMATED.",
        "Then I watched the result. Same background. Flat movement. Robotic narration. Template captions. It looked automated because it was automated.",
        "source",
        ("SAME BACKGROUND", "FLAT MOTION", "ROBOTIC VOICE", "TEMPLATE CAPTIONS"),
        source_offset=16.0,
    ),
    DocumentaryScene(
        "THE FALSE POSITIVE",
        "PASSING THE CHECKS\nWASN'T ENOUGH.",
        "The quality gate said pass: full HD, clean audio, correct duration, no broken frames. But the only test that mattered—would a person keep watching?—failed.",
        "verdict",
        ("TECHNICAL CHECKS", "VIEWER VALUE"),
    ),
    DocumentaryScene(
        "THE DECISION",
        "I STOPPED\nTHE UPLOAD.",
        "So I stopped the upload. The next version will use real screenshots, source material, licensed footage, custom charts, natural narration, and an actual editorial point of view.",
        "pivot",
        ("REAL EVIDENCE", "NATURAL VOICE", "CUSTOM VISUALS", "HUMAN REVIEW"),
    ),
    DocumentaryScene(
        "THE NEW RULE",
        "SHOW THE WORK.\nKEEP THE VALUE.",
        "This channel will not pretend AI is magic. I will show the costs, failures, code, and numbers, and keep only the videos worth a human click.",
        "principle",
        ("COSTS", "FAILURES", "CODE", "NUMBERS"),
    ),
    DocumentaryScene(
        "BUILD LOG 001",
        "CAN A ₹0 AI CHANNEL\nBECOME WORTH WATCHING?",
        "Can a zero-cost AI channel become genuinely worth watching? This rejected video is day one. Now we rebuild it properly.",
        "finale",
        ("RESEARCH", "BUILD", "REVIEW", "PUBLISH"),
    ),
)


class GeminiNarrator:
    """Controllable TTS through Gemini's REST Interactions API."""

    ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview").strip()
        self.voice = os.getenv("GEMINI_TTS_VOICE", "Charon").strip()
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for the documentary pilot voice")

    @staticmethod
    def _find_audio(value: Any) -> tuple[bytes, str, int] | None:
        if isinstance(value, dict):
            mime = str(value.get("mime_type") or value.get("mimeType") or "")
            data = value.get("data")
            value_type = str(value.get("type") or "")
            if isinstance(data, str) and (mime.startswith("audio/") or value_type == "audio"):
                rate = int(value.get("sample_rate") or value.get("sampleRate") or 24000)
                return base64.b64decode(data), mime or "audio/l16", rate
            for nested in value.values():
                found = GeminiNarrator._find_audio(nested)
                if found:
                    return found
        elif isinstance(value, list):
            for nested in value:
                found = GeminiNarrator._find_audio(nested)
                if found:
                    return found
        return None

    @staticmethod
    def _write_audio(path: Path, audio: bytes, mime_type: str, sample_rate: int) -> None:
        mime_parts = [part.strip() for part in mime_type.lower().split(";") if part.strip()]
        media_type = mime_parts[0] if mime_parts else ""
        parameters: dict[str, str] = {}
        for part in mime_parts[1:]:
            key, separator, value = part.partition("=")
            if separator:
                parameters[key.strip()] = value.strip()

        if audio.startswith(b"RIFF") or media_type in {"audio/wav", "audio/x-wav"}:
            path.write_bytes(audio)
            return
        if media_type not in {"audio/l16", ""}:
            raise RuntimeError(f"Gemini returned unsupported audio type: {mime_type}")
        output_rate = int(parameters.get("rate", sample_rate or 24000))
        output_channels = int(parameters.get("channels", 1))
        with wave.open(str(path), "wb") as output:
            output.setnchannels(output_channels)
            output.setsampwidth(2)
            output.setframerate(output_rate)
            output.writeframes(audio)

    def synthesize(self, transcript: str, output_path: Path) -> None:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("Install requirements.txt before using Gemini narration") from exc

        direction = f"""# AUDIO PROFILE
A confident, thoughtful technology documentary narrator. Natural global English, warm and conversational, never theatrical or salesy.

# DIRECTOR'S NOTES
Medium-fast pace. Short deliberate pauses after punch lines. Vary emphasis naturally. Sound like a real creator explaining an honest failure to one viewer. Do not read headings or directions.

# TRANSCRIPT
{transcript}
"""
        response = requests.post(
            self.ENDPOINT,
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            json={
                "model": self.model,
                "input": direction,
                "response_format": {"type": "audio"},
                "generation_config": {"speech_config": [{"voice": self.voice}]},
            },
            timeout=180,
        )
        if not response.ok:
            raise RuntimeError(f"Gemini TTS failed ({response.status_code}): {response.text[:600]}")
        payload = response.json()
        found = self._find_audio(payload)
        if not found:
            raise RuntimeError(f"Gemini TTS response had no audio: {json.dumps(payload)[:600]}")
        self._write_audio(output_path, *found)


class DocumentaryRenderer:
    WIDTH = 1920
    HEIGHT = 1080
    FPS = 24
    BG = (7, 11, 18)
    PANEL = (15, 22, 34)
    WHITE = (244, 247, 250)
    MUTED = (152, 166, 185)
    CYAN = (69, 214, 209)
    RED = (255, 78, 92)
    AMBER = (255, 194, 92)

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.font_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        self.font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    def _font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(self.font_bold if bold else self.font_regular, size)

    @staticmethod
    def _run(command: list[str]) -> None:
        subprocess.run(command, check=True)

    @staticmethod
    def _duration(path: Path) -> float:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return float(result.stdout.strip())

    def _background(self) -> Image.Image:
        image = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.BG)
        draw = ImageDraw.Draw(image)
        for y in range(self.HEIGHT):
            progress = y / self.HEIGHT
            color = (7 + int(7 * progress), 11 + int(11 * progress), 18 + int(18 * progress))
            draw.line((0, y, self.WIDTH, y), fill=color)
        draw.ellipse((1280, -520, 2260, 460), fill=(15, 55, 66))
        draw.ellipse((-540, 650, 420, 1610), fill=(32, 19, 36))
        return image.filter(ImageFilter.GaussianBlur(55))

    def _brand(self, draw: ImageDraw.ImageDraw, index: int) -> None:
        draw.rounded_rectangle((76, 58, 420, 112), radius=27, fill=(19, 29, 43), outline=(42, 57, 76), width=2)
        draw.ellipse((97, 77, 116, 96), fill=self.CYAN)
        draw.text((132, 71), "AUTOTUBE / BUILD LOG", font=self._font(24, True), fill=self.WHITE)
        draw.text((1775, 72), f"0{index + 1}", font=self._font(28, True), fill=self.MUTED)

    def _eyebrow_title(
        self,
        draw: ImageDraw.ImageDraw,
        scene: DocumentaryScene,
        x: int = 100,
        y: int = 188,
        title_size: int = 74,
    ) -> None:
        draw.text((x, y), scene.eyebrow, font=self._font(26, True), fill=self.CYAN)
        y += 62
        for line in scene.title.split("\n"):
            draw.text((x, y), line, font=self._font(title_size, True), fill=self.WHITE, stroke_width=1)
            y += title_size + 14

    def _card_metrics(self, image: Image.Image, scene: DocumentaryScene) -> None:
        draw = ImageDraw.Draw(image)
        self._eyebrow_title(draw, scene)
        draw.rounded_rectangle((990, 176, 1818, 900), radius=34, fill=self.PANEL, outline=(47, 63, 83), width=3)
        draw.rectangle((990, 176, 1818, 244), fill=(25, 34, 49))
        for index, color in enumerate(((255, 95, 99), (255, 190, 75), (79, 210, 135))):
            x = 1027 + index * 34
            draw.ellipse((x, 198, x + 16, 214), fill=color)
        draw.text((1147, 194), "render_report.json", font=self._font(23, True), fill=(177, 188, 205))
        labels = (("SERVER", "2 CPU / 1 GB"), ("OUTPUT", "46.5 SEC / FULL HD"), ("SIZE", "15.09 MB"), ("RENDER", "03:22"))
        y = 302
        for label, value in labels:
            draw.text((1052, y), label, font=self._font(23, True), fill=self.MUTED)
            draw.text((1052, y + 38), value, font=self._font(42, True), fill=self.WHITE)
            draw.line((1052, y + 106, 1753, y + 106), fill=(44, 57, 74), width=2)
            y += 135
        draw.rounded_rectangle((98, 702, 850, 810), radius=24, fill=(16, 43, 44), outline=(40, 104, 105), width=2)
        draw.text((137, 732), "PIPELINE STATUS", font=self._font(24, True), fill=self.MUTED)
        draw.text((545, 722), "PASSED", font=self._font(43, True), fill=self.CYAN)

    def _card_verdict(self, image: Image.Image, scene: DocumentaryScene) -> None:
        draw = ImageDraw.Draw(image)
        self._eyebrow_title(draw, scene)
        panels = ((980, "TECHNICAL CHECKS", "PASS", self.CYAN, 0.96), (1395, "VIEWER VALUE", "FAIL", self.RED, 0.18))
        for x, label, verdict, color, score in panels:
            draw.rounded_rectangle((x, 210, x + 350, 892), radius=32, fill=self.PANEL, outline=(47, 63, 83), width=3)
            draw.text((x + 34, 252), label, font=self._font(22, True), fill=self.MUTED)
            bottom, bar_height = 735, 350
            draw.rounded_rectangle((x + 78, bottom - bar_height, x + 272, bottom), radius=32, fill=(30, 41, 56))
            filled = int(bar_height * score)
            draw.rounded_rectangle((x + 78, bottom - filled, x + 272, bottom), radius=32, fill=color)
            draw.text((x + 105, 790), verdict, font=self._font(48, True), fill=color)
        draw.rounded_rectangle((100, 733, 828, 845), radius=24, fill=(46, 20, 29), outline=(105, 39, 50), width=2)
        draw.text((138, 765), "WOULD YOU KEEP WATCHING?", font=self._font(29, True), fill=self.RED)

    def _card_pivot(self, image: Image.Image, scene: DocumentaryScene) -> None:
        draw = ImageDraw.Draw(image)
        self._eyebrow_title(draw, scene)
        colors = (self.CYAN, (91, 154, 255), self.AMBER, (188, 119, 255))
        for index, point in enumerate(scene.points):
            row, col = divmod(index, 2)
            x, y = 850 + col * 470, 285 + row * 280
            draw.rounded_rectangle((x, y, x + 410, y + 220), radius=30, fill=self.PANEL, outline=(48, 65, 86), width=3)
            draw.rounded_rectangle((x + 28, y + 30, x + 91, y + 93), radius=17, fill=colors[index])
            draw.text((x + 60, y + 61), str(index + 1), font=self._font(28, True), fill=(7, 11, 18), anchor="mm")
            for line_index, line in enumerate(wrap(point, 16)[:2]):
                draw.text((x + 30, y + 124 + line_index * 38), line, font=self._font(30, True), fill=self.WHITE)
        draw.line((100, 670, 705, 670), fill=self.RED, width=9)
        draw.text((100, 702), "UPLOAD DISABLED", font=self._font(31, True), fill=self.RED)
        draw.text((100, 753), "until a human approves it", font=self._font(27), fill=self.MUTED)

    def _card_principle(self, image: Image.Image, scene: DocumentaryScene) -> None:
        draw = ImageDraw.Draw(image)
        self._eyebrow_title(draw, scene)
        for index, (x, label) in enumerate(zip((110, 545, 980, 1415), scene.points)):
            color = self.CYAN if index % 2 == 0 else self.AMBER
            draw.rounded_rectangle((x, 640, x + 360, 860), radius=31, fill=self.PANEL, outline=(47, 63, 83), width=3)
            draw.text((x + 34, 679), f"0{index + 1}", font=self._font(24, True), fill=color)
            draw.text((x + 34, 758), label, font=self._font(34, True), fill=self.WHITE)
        draw.text((1110, 238), "AI", font=self._font(210, True), fill=(31, 44, 59))
        draw.line((1100, 445, 1655, 445), fill=self.RED, width=15)
        draw.text((1160, 482), "IS NOT THE STORY", font=self._font(34, True), fill=self.RED)

    def _card_finale(self, image: Image.Image, scene: DocumentaryScene) -> None:
        draw = ImageDraw.Draw(image)
        self._eyebrow_title(draw, scene, x=150, y=178)
        x, y = 152, 675
        colors = (self.CYAN, (91, 154, 255), self.AMBER, self.RED)
        for index, (label, color) in enumerate(zip(scene.points, colors)):
            draw.rounded_rectangle((x, y, x + 330, y + 103), radius=26, fill=self.PANEL, outline=color, width=3)
            draw.text((x + 165, y + 52), label, font=self._font(28, True), fill=self.WHITE, anchor="mm")
            if index < len(scene.points) - 1:
                draw.line((x + 342, y + 52, x + 383, y + 52), fill=(77, 91, 110), width=4)
                draw.polygon(((x + 383, y + 42), (x + 403, y + 52), (x + 383, y + 62)), fill=(77, 91, 110))
            x += 410
        draw.rounded_rectangle((151, 858, 481, 928), radius=35, fill=self.RED)
        draw.text((316, 893), "DAY 1 / REBUILD", font=self._font(26, True), fill=self.WHITE, anchor="mm")

    def _static_card(self, scene: DocumentaryScene, index: int, output: Path) -> None:
        image = self._background()
        self._brand(ImageDraw.Draw(image), index)
        if scene.mode == "metrics":
            self._card_metrics(image, scene)
        elif scene.mode == "verdict":
            self._card_verdict(image, scene)
        elif scene.mode == "pivot":
            self._card_pivot(image, scene)
        elif scene.mode == "principle":
            self._card_principle(image, scene)
        elif scene.mode == "finale":
            self._card_finale(image, scene)
        else:
            raise ValueError(f"Unknown static scene: {scene.mode}")
        image.save(output, quality=96)

    def _video_overlay(self, scene: DocumentaryScene, index: int, output: Path) -> None:
        overlay = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay, "RGBA")
        draw.rectangle((0, 0, 650, self.HEIGHT), fill=(5, 9, 16, 238))
        draw.rectangle((650, 0, self.WIDTH, 175), fill=(5, 9, 16, 170))
        draw.rectangle((650, 892, self.WIDTH, self.HEIGHT), fill=(5, 9, 16, 195))
        draw.rounded_rectangle((700, 205, 1800, 824), radius=25, outline=(111, 126, 148, 220), width=4)
        self._brand(draw, index)
        self._eyebrow_title(draw, scene, x=82, y=205, title_size=54)
        if scene.mode == "hook":
            draw.rounded_rectangle((82, 696, 505, 804), radius=24, fill=self.RED)
            draw.text((293, 751), "REJECTED", font=self._font(45, True), fill=self.WHITE, anchor="mm")
            draw.text((82, 843), "The first output was not publishable.", font=self._font(24), fill=self.MUTED)
        else:
            y = 615
            for point in scene.points:
                draw.ellipse((82, y + 11, 99, y + 28), fill=self.RED)
                draw.text((116, y), point, font=self._font(24, True), fill=self.WHITE)
                y += 56
            draw.text((720, 850), "ACTUAL V3 OUTPUT / NOT UPLOADED", font=self._font(23, True), fill=self.RED)
        overlay.save(output)

    def _render_scene(self, scene: DocumentaryScene, index: int, duration: float, source_video: Path, work: Path) -> Path:
        clip = work / f"scene-{index:02d}.mp4"
        if scene.mode in {"hook", "source"}:
            overlay = work / f"overlay-{index:02d}.png"
            self._video_overlay(scene, index, overlay)
            filter_graph = (
                "[0:v]split=2[bgsrc][fgsrc];"
                "[bgsrc]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,gblur=sigma=26,eq=brightness=-0.38:saturation=0.55[bg];"
                "[fgsrc]scale=1100:618[fg];"
                "[bg][fg]overlay=700:205[base];[base][1:v]overlay=0:0,format=yuv420p[v]"
            )
            self._run([
                "ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-ss", str(scene.source_offset), "-i", str(source_video),
                "-loop", "1", "-i", str(overlay), "-filter_complex", filter_graph, "-map", "[v]", "-t", f"{duration:.3f}",
                "-r", str(self.FPS), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", str(clip),
            ])
        else:
            card = work / f"card-{index:02d}.png"
            self._static_card(scene, index, card)
            zoom = "zoompan=z='min(zoom+0.00035,1.045)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=24,format=yuv420p"
            self._run([
                "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(card), "-vf", zoom, "-t", f"{duration:.3f}",
                "-r", str(self.FPS), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", str(clip),
            ])
        return clip

    @staticmethod
    def _ass_time(seconds: float) -> str:
        centiseconds = max(0, int(seconds * 100))
        hours, remainder = divmod(centiseconds, 360000)
        minutes, remainder = divmod(remainder, 6000)
        secs, cs = divmod(remainder, 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"

    def _write_captions(self, scenes: tuple[DocumentaryScene, ...], durations: list[float], output: Path) -> None:
        header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,48,&H00FFFFFF,&H00FFFFFF,&H00000000,&HB0000710,-1,0,0,0,100,100,0,0,3,0,0,2,120,120,55,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events: list[str] = []
        scene_start = 0.0
        for scene, duration in zip(scenes, durations):
            words = scene.narration.split()
            chunks = [words[index : index + 7] for index in range(0, len(words), 7)]
            cursor = scene_start
            for chunk in chunks:
                chunk_duration = duration * len(chunk) / max(1, len(words))
                text = " ".join(chunk).replace("{", "(").replace("}", ")")
                events.append(f"Dialogue: 0,{self._ass_time(cursor)},{self._ass_time(cursor + chunk_duration)},Caption,,0,0,0,,{text}")
                cursor += chunk_duration
            scene_start += duration
        output.write_text(header + "\n".join(events) + "\n", encoding="utf-8")

    def _thumbnail(self, source_video: Path, output: Path, work: Path) -> None:
        frame_path = work / "thumbnail-source.jpg"
        self._run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "8", "-i", str(source_video), "-frames:v", "1", str(frame_path)])
        source = Image.open(frame_path).convert("RGB")
        source = source.resize((650, 366), Image.Resampling.LANCZOS)
        source = ImageEnhance.Brightness(source).enhance(0.72)
        canvas = self._background().resize((1280, 720), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(canvas)
        canvas.paste(source, (590, 178))
        draw.rounded_rectangle((588, 176, 1242, 546), radius=24, outline=(118, 133, 154), width=5)
        draw.line((655, 205, 1170, 520), fill=self.RED, width=26)
        draw.line((1170, 205, 655, 520), fill=self.RED, width=26)
        draw.text((65, 74), "I REJECTED", font=self._font(72, True), fill=self.WHITE)
        draw.text((65, 158), "MY AI VIDEO", font=self._font(72, True), fill=self.WHITE)
        draw.rounded_rectangle((65, 304, 502, 389), radius=22, fill=self.RED)
        draw.text((283, 347), "NOT GOOD ENOUGH", font=self._font(31, True), fill=self.WHITE, anchor="mm")
        draw.text((65, 501), "₹0 SYSTEM  /  DAY 1", font=self._font(29, True), fill=self.CYAN)
        canvas.save(output, quality=94, optimize=True)

    def render(self, job_id: str, source_video: Path, narration_wav: Path | None = None, scenes: tuple[DocumentaryScene, ...] = PILOT_SCENES) -> dict[str, Path | float]:
        if not source_video.exists():
            raise FileNotFoundError(f"Source video not found: {source_video}")
        job_dir = self.data_dir / job_id
        work = job_dir / "work"
        work.mkdir(parents=True, exist_ok=True)
        voice_path = job_dir / "narration.wav"
        transcript = " ".join(scene.narration for scene in scenes)
        if narration_wav:
            self._run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(narration_wav), "-ac", "1", "-ar", "24000", str(voice_path)])
        else:
            GeminiNarrator().synthesize(transcript, voice_path)
        audio_duration = self._duration(voice_path)
        word_counts = [len(scene.narration.split()) for scene in scenes]
        durations = [audio_duration * count / sum(word_counts) for count in word_counts]

        clips = []
        for index, (scene, duration) in enumerate(zip(scenes, durations)):
            print(f"  [pilot] Scene {index + 1}/{len(scenes)}: {scene.eyebrow} ({duration:.1f}s)", flush=True)
            clips.append(self._render_scene(scene, index, duration, source_video, work))

        concat_file = work / "concat.txt"
        concat_file.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
        visuals = work / "visuals.mp4"
        self._run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(visuals)])
        captions = work / "captions.ass"
        self._write_captions(scenes, durations, captions)
        final = job_dir / "final.mp4"
        escaped_ass = str(captions).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        self._run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(visuals), "-i", str(voice_path), "-vf", f"ass='{escaped_ass}'",
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "faster", "-crf", "19", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final),
        ])
        thumbnail = job_dir / "thumbnail.jpg"
        self._thumbnail(source_video, thumbnail, work)
        return {"video_path": final, "thumbnail_path": thumbnail, "duration": self._duration(final)}
