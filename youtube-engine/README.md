# AutoTube V3 — Autonomous Character-Simulation Channel

AutoTube V3 is a CPU-only YouTube production system for original robot challenges,
science simulations and future-tech entertainment. It is designed for the small Oracle
Cloud VM used by this project and keeps paid video-generation APIs out of the pipeline.

The channel has a reusable original cast:

- **Nova** — blue team leader
- **Mira** — purple analyst
- **Bolt** — orange risk-taker
- **Pix** — green problem-solver and underdog

The characters and situations are original. The pipeline does not depend on celebrity
likenesses, copied cartoon characters or mass-produced stock-video templates.

## What V3 automates

1. A timer starts production at the configured publishing windows.
2. Free RSS signals and recent topics inform the idea engine.
3. Gemini's free tier scores original challenge concepts.
4. Gemini writes a sourced story, narration and shot-level storyboard.
5. Piper generates narration locally.
6. Pillow and FFmpeg render reusable characters plus frame-by-frame bridge, gravity,
   maze and Mars simulations.
7. The renderer adds captions, shot labels, motion and a challenge-style thumbnail.
8. A quality gate rejects missing, corrupt or unusually short output.
9. The YouTube Data API can upload the video and thumbnail.
10. SQLite records completed and failed topics to reduce close repeats.

Uploads remain disabled by default. Keep all initial YouTube uploads `private` until
several generated videos have been reviewed for story quality, factual accuracy,
pronunciation, pacing, visual repetition and thumbnail quality.

## Cost policy

- self-hosted Python worker
- Gemini API free tier
- Piper local TTS
- Pillow + FFmpeg procedural animation
- SQLite
- YouTube Data API quota
- systemd timer on the existing Oracle VM

No paid voice, stock-footage, video-generation or automation SaaS is required for V3.

## Current deployment path

The existing ~1 GB Oracle VM uses the native Python/systemd setup. Do not activate the
n8n workflow and the systemd timer together, because that would create duplicate jobs.
The n8n workflow remains in the repository as an optional alternative for a larger server.

### 1. Native setup

```bash
cd /opt/autotube-repo/youtube-engine
bash scripts/setup_native.sh
```

Add the free Gemini key to `.env`. Keep these safety settings during testing:

```dotenv
UPLOAD_ENABLED=false
YOUTUBE_PRIVACY_STATUS=private
```

### 2. Verify Gemini

```bash
.venv/bin/python scripts/test_gemini.py
```

### 3. Render the V3 character prototype

```bash
time .venv/bin/python scripts/test_v3.py
```

This produces a roughly one-minute bridge-collapse challenge featuring Nova, Mira,
Bolt and Pix. Review both the returned `final.mp4` and `thumbnail.jpg` before running
a full Gemini-generated episode.

### 4. Run one full episode without upload

```bash
time .venv/bin/python scripts/run_once.py
```

### 5. Install the production timer only after approval

```bash
sudo cp systemd/autotube.service /etc/systemd/system/
sudo cp systemd/autotube.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now autotube.timer
systemctl list-timers autotube.timer
```

The timer starts rendering before the target English-language publishing windows. It is
not enabled by the repository itself.

## YouTube private-upload setup

Create a Google Cloud project, enable **YouTube Data API v3**, create an OAuth Desktop
client, and save it as:

```text
secrets/client_secret.json
```

The repository ignores the `secrets/` directory. Never commit OAuth files or API keys.

Run the one-time authorization:

```bash
.venv/bin/python scripts/youtube_auth.py
```

After `secrets/youtube_token.json` is created, first change only:

```dotenv
UPLOAD_ENABLED=true
YOUTUBE_PRIVACY_STATUS=private
```

Do not switch to public upload until the private tests have been inspected and approved.

## Optional API / n8n mode

On a larger machine, Docker Compose exposes the worker at `127.0.0.1:8000` and n8n at
`127.0.0.1:5678`.

```bash
docker compose up -d
curl http://localhost:8000/health
curl -X POST http://localhost:8000/run
```

Only one worker job can run at a time; a second `/run` request receives HTTP 409.
