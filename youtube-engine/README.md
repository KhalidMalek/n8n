# AutoTube V1 — Free Autonomous YouTube Pipeline

AutoTube V1 is the first deployable version of an automated YouTube production system for an **animated science / future-technology / “what if?”** channel.

## What V1 automates

1. n8n triggers production on Monday, Wednesday and Saturday.
2. The worker collects free RSS/news signals.
3. Gemini free tier proposes and scores original topics.
4. Research snippets are collected before writing.
5. Gemini writes a sourced episode, scene plan, metadata and thumbnail text.
6. Kokoro generates narration locally (no per-character fee).
7. Pillow + FFmpeg create original procedural visuals and assemble the video.
8. A quality gate rejects missing/very short renders.
9. The YouTube Data API uploads the video and thumbnail.
10. SQLite records produced topics so future episodes avoid close repeats.

**Important:** V1 defaults all YouTube uploads to `private`. Do not switch to public until several generated videos have been manually reviewed for factual accuracy, pacing, visual quality and repetition. V2 will add richer simulations/animation, Shorts generation and analytics feedback before public unattended publishing.

## Cost policy

The software stack is free/open-source or uses a free API tier:

- n8n Community Edition (self-hosted)
- Python
- Gemini API free tier
- Kokoro local TTS
- FFmpeg
- Pillow
- SQLite
- YouTube Data API quota

No paid video-generation, voice, stock-footage or automation SaaS is required.

## Hosting

Use a Linux machine with Docker. A free Oracle Cloud Always Free VM can run the orchestration/CPU V1 if capacity is available. A home PC can also run it. Hostinger Web App Hosting is not the recommended target because this stack needs Docker/system packages, persistent state and local rendering. A Hostinger VPS can run the same Docker Compose stack later.

## Setup

### 1. Clone and configure

```bash
cp .env.example .env
```

Add a free `GEMINI_API_KEY` to `.env`.

### 2. YouTube API one-time setup

Create a Google Cloud project, enable **YouTube Data API v3**, create an OAuth Desktop client, and download it as:

```text
secrets/client_secret.json
```

The repository intentionally ignores the entire `secrets/` directory. Never commit OAuth files or API keys.

### 3. Build

```bash
docker compose build
```

### 4. One-time YouTube authorization

```bash
docker compose run --rm -p 8765:8765 worker python scripts/youtube_auth.py
```

Open the Google authorization URL printed by the command in a browser. After approval, Google redirects to `localhost:8765` and the token is saved under `secrets/`. Future uploads can then run unattended.

### 5. Start

```bash
docker compose up -d
```

Open n8n on port `5678`, import `n8n/autotube.workflow.json`, and publish/activate the workflow.

Worker health check:

```bash
curl http://localhost:8000/health
```

Manual pipeline test:

```bash
curl -X POST http://localhost:8000/run
```

The worker returns a job ID. Check it with:

```bash
curl http://localhost:8000/status/JOB_ID
```

## Before public automation

Keep `YOUTUBE_PRIVACY_STATUS=private` until V1 produces repeatably acceptable output. Public unattended publishing should only be enabled after the richer V2 visual engine, analytics feedback and stronger originality/duplication checks are added.
