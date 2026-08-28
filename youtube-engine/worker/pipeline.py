from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import feedparser
from dotenv import load_dotenv
from google import genai

from worker.render import VideoRenderer
from worker.youtube_upload import YouTubeUploader

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    gemini_api_key: str
    gemini_model: str
    gemini_fallback_models: list[str]
    niche: str
    language: str
    data_dir: Path
    upload_enabled: bool
    privacy_status: str
    category_id: str
    rss_feeds: list[str]

    @classmethod
    def from_env(cls) -> "Settings":
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("GEMINI_API_KEY is missing. Copy .env.example to .env and add a free Gemini API key.")
        return cls(
            gemini_api_key=key,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.7-flash").strip(),
            gemini_fallback_models=[
                x.strip()
                for x in os.getenv(
                    "GEMINI_FALLBACK_MODELS",
                    "gemini-3.5-flash,gemini-3.5-flash-lite",
                ).split(",")
                if x.strip()
            ],
            niche=os.getenv("CHANNEL_NICHE", "Animated science and future technology what-if simulations"),
            language=os.getenv("VIDEO_LANGUAGE", "en"),
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            upload_enabled=_env_bool("UPLOAD_ENABLED", False),
            privacy_status=os.getenv("YOUTUBE_PRIVACY_STATUS", "private"),
            category_id=os.getenv("YOUTUBE_CATEGORY_ID", "28"),
            rss_feeds=[x.strip() for x in os.getenv("RSS_FEEDS", "").split(",") if x.strip()],
        )


class Pipeline:
    def __init__(self) -> None:
        self.settings = Settings.from_env()
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.settings.data_dir / "autotube.sqlite3"
        self.client = genai.Client(api_key=self.settings.gemini_api_key)
        self.renderer = VideoRenderer(self.settings.data_dir)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE,
                    topic TEXT NOT NULL,
                    title TEXT,
                    status TEXT NOT NULL,
                    youtube_video_id TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _is_transient_gemini_error(exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        if status_code in {429, 500, 502, 503, 504}:
            return True
        message = str(exc).lower()
        return any(
            marker in message
            for marker in (
                "503",
                "unavailable",
                "high demand",
                "resource exhausted",
                "rate limit",
                "429",
                "deadline exceeded",
                "temporarily",
            )
        )

    def _gemini_json(self, prompt: str) -> Any:
        models: list[str] = []
        for model in [self.settings.gemini_model, *self.settings.gemini_fallback_models]:
            if model and model not in models:
                models.append(model)

        last_error: Exception | None = None
        for model_index, model in enumerate(models):
            for attempt in range(1, 3):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config={"response_mime_type": "application/json"},
                    )
                    payload = json.loads((response.text or "").strip())
                    if model != self.settings.gemini_model:
                        print(f"Gemini fallback succeeded with {model}.", flush=True)
                    return payload
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    if not self._is_transient_gemini_error(exc):
                        raise
                    if attempt < 2:
                        delay = 8 * attempt
                        print(
                            f"Gemini {model} temporarily unavailable; retrying in {delay}s...",
                            flush=True,
                        )
                        time.sleep(delay)
                    elif model_index < len(models) - 1:
                        print(
                            f"Gemini {model} still unavailable; switching to {models[model_index + 1]}...",
                            flush=True,
                        )

        raise RuntimeError(
            "All configured free-tier Gemini models were temporarily unavailable. "
            f"Tried: {', '.join(models)}. Last error: {last_error}"
        ) from last_error

    def _recent_topics(self, limit: int = 50) -> list[str]:
        with sqlite3.connect(self.db_path) as con:
            rows = con.execute("SELECT topic FROM videos ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [r[0] for r in rows]

    @staticmethod
    def _clean_html(value: str) -> str:
        return re.sub(r"<[^>]+>", " ", value or "").replace("&nbsp;", " ").strip()

    def _feed_items(self, topic: str | None = None, limit: int = 24) -> list[dict[str, str]]:
        urls = list(self.settings.rss_feeds)
        if topic:
            urls.append(f"https://news.google.com/rss/search?q={quote_plus(topic)}&hl=en-US&gl=US&ceid=US:en")
        items: list[dict[str, str]] = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:10]:
                    items.append(
                        {
                            "title": self._clean_html(entry.get("title", "")),
                            "summary": self._clean_html(entry.get("summary", ""))[:800],
                            "link": entry.get("link", ""),
                            "published": entry.get("published", ""),
                        }
                    )
            except Exception:
                continue
        return items[:limit]

    def choose_topic(self) -> dict[str, Any]:
        recent = self._recent_topics()
        signals = self._feed_items(limit=30)
        prompt = f"""
You run a YouTube channel in this niche: {self.settings.niche}.
Choose ONE video topic with strong curiosity/click potential while still allowing accurate, educational treatment.
The channel must avoid mass-produced/repetitive content and cannot copy titles or storylines.

Recent topics already used (avoid close repeats):
{json.dumps(recent, ensure_ascii=False)}

Fresh public signals (use only as inspiration, not as a script):
{json.dumps(signals, ensure_ascii=False)[:14000]}

Generate 12 candidates, score each from 0-100 on clickability, novelty, evergreen value, visual potential, and advertiser friendliness.
Prefer animated "What if...?", future technology, space, AI, engineering, or science scenarios.
Return JSON exactly as:
{{"selected": {{"topic":"...","angle":"...","score":0}}, "candidates":[...]}}
"""
        return self._gemini_json(prompt)["selected"]

    def research(self, topic: str) -> list[dict[str, str]]:
        items = self._feed_items(topic=topic, limit=30)
        if not items:
            raise RuntimeError("No research sources were retrieved; refusing to generate an unsourced episode.")
        return items

    def create_episode(self, topic: dict[str, Any], sources: list[dict[str, str]]) -> dict[str, Any]:
        prompt = f"""
Create an original YouTube episode for the niche: {self.settings.niche}.
Topic: {topic['topic']}
Angle: {topic.get('angle','')}

Research snippets and links:
{json.dumps(sources, ensure_ascii=False)[:22000]}

Rules:
- Educational entertainment, not financial/medical/legal advice.
- Do not invent factual claims. If the topic is hypothetical, clearly distinguish assumptions from established facts.
- Never copy source wording.
- Aim for 6-8 minutes in V1.
- Hook immediately; no generic welcome intro.
- Make every scene materially different.
- Give each scene a concise visual heading plus 2-4 short on-screen points.
- Narration should sound natural when spoken.
- Include source URLs used so they can be listed in the description.

Return JSON exactly in this shape:
{{
  "working_title":"...",
  "hook":"...",
  "scenes":[
    {{"heading":"...","narration":"...","points":["...","..."]}}
  ],
  "source_urls":["https://..."],
  "description_summary":"2-3 original sentences"
}}
"""
        episode = self._gemini_json(prompt)
        if len(episode.get("scenes", [])) < 5:
            raise RuntimeError("Episode failed quality gate: fewer than 5 scenes.")
        return episode

    def create_metadata(self, episode: dict[str, Any]) -> dict[str, Any]:
        prompt = f"""
Create YouTube metadata for this original animated science/future-tech episode.
Episode title idea: {episode['working_title']}
Summary: {episode['description_summary']}
Sources: {json.dumps(episode.get('source_urls', []))}

Return JSON exactly:
{{
 "title":"<=70 characters, specific and curiosity-driven, not deceptive",
 "description":"Concise description followed by a Sources section with the supplied URLs",
 "tags":["8-15 relevant tags"],
 "thumbnail_text":"2-4 words max"
}}
"""
        return self._gemini_json(prompt)

    def _insert_record(self, job_id: str, topic: str) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                "INSERT OR REPLACE INTO videos(job_id, topic, status, created_at) VALUES(?,?,?,?)",
                (job_id, topic, "running", datetime.now(timezone.utc).isoformat()),
            )

    def _finish_record(self, job_id: str, title: str, status: str, video_id: str | None = None) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                "UPDATE videos SET title=?, status=?, youtube_video_id=? WHERE job_id=?",
                (title, status, video_id, job_id),
            )

    def run(self, job_id: str) -> dict[str, Any]:
        topic = self.choose_topic()
        self._insert_record(job_id, topic["topic"])
        sources = self.research(topic["topic"])
        episode = self.create_episode(topic, sources)
        metadata = self.create_metadata(episode)

        render = self.renderer.render_episode(job_id, episode, metadata)
        self.renderer.quality_check(render["video_path"])

        video_id: str | None = None
        status = "rendered"
        if self.settings.upload_enabled:
            uploader = YouTubeUploader(
                privacy_status=self.settings.privacy_status,
                category_id=self.settings.category_id,
            )
            video_id = uploader.upload(
                video_path=render["video_path"],
                thumbnail_path=render["thumbnail_path"],
                title=metadata["title"],
                description=metadata["description"],
                tags=metadata.get("tags", []),
            )
            status = "uploaded"

        self._finish_record(job_id, metadata["title"], status, video_id)
        return {
            "topic": topic,
            "title": metadata["title"],
            "status": status,
            "upload_enabled": self.settings.upload_enabled,
            "youtube_video_id": video_id,
            "privacy_status": self.settings.privacy_status if self.settings.upload_enabled else None,
            "video_path": str(render["video_path"]),
            "thumbnail_path": str(render["thumbnail_path"]),
        }
