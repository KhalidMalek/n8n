# AutoTube Pilot — Evidence-Led Technology Documentary

> **Creative reset:** the V3 robot simulation passed its technical checks but failed
> the human watchability review. Do not upload it and do not use the recurring-robot
> template for production. The current target format is an evidence-led,
> build-in-public mini-documentary with real project footage and human approval.

The current experiment is designed for the existing two-core, ~1 GB Oracle Cloud VM.
It treats AI as a production assistant, while the topic, evidence, editorial decision
and final approval remain human-controlled.

## What the pilot does

1. Finds the real rejected V3 render already stored on the server.
2. Uses a fixed, reviewed build-log script based on the real experiment.
3. Generates a directed documentary narration with Gemini TTS.
4. Combines the real footage with original metrics, charts and motion graphics.
5. Burns readable captions and creates a new evidence-led thumbnail.
6. Checks the private render's duration and media integrity.
7. Stops. It does not call the YouTube uploader or production timer.

Uploads remain disabled by default. Keep all initial YouTube uploads `private` until
several generated videos have been reviewed for story quality, factual accuracy,
pronunciation, pacing, visual repetition and thumbnail quality.

## Current private pilot

The first redesigned story is **"I Rejected My AI Video"**. It turns the failed V3
output into evidence inside a short documentary about what worked technically and what
failed creatively. It uses:

- the real rejected V3 clip;
- real VM and render measurements;
- custom documentary motion graphics and captions;
- Gemini's controllable TTS voice instead of the robotic Piper voice;
- a visible human editorial decision; and
- no stock footage or borrowed creator format.

Render it on the server after pulling the latest code:

```bash
cd /opt/autotube-repo/youtube-engine
.venv/bin/python scripts/test_documentary.py
```

The script automatically finds the newest `data/v3-bridge-test-*/final.mp4`. It creates
a new `data/documentary-pilot-*/final.mp4` and `thumbnail.jpg`, but never calls the
YouTube uploader. Review both files manually before any next step.

## Cost policy

- self-hosted Python worker
- Gemini API free tier
- Gemini controllable TTS for the reviewed pilot
- Pillow + FFmpeg documentary motion graphics

No paid voice, stock footage, video-generation or automation SaaS is required for this
pilot. Gemini's preview TTS availability and free-tier limits can change, so keep the
model configurable in `.env`.

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

### 3. Render the redesigned private pilot

```bash
time .venv/bin/python scripts/test_documentary.py
```

Review both the returned `final.mp4` and `thumbnail.jpg`. Do not upload them yet.

### Legacy V3 diagnostic only

```bash
time .venv/bin/python scripts/test_v3.py
```

The recurring robot renderer remains in the repository as the record of the failed
prototype and as source footage for this pilot. It is not the production format.

### Production automation remains paused

Do not run `scripts/run_once.py`, enable uploads, or install the timer while the channel
format is still being validated. Those actions come only after multiple private pilots
pass a human creative review.

The legacy timer commands are retained here for future reference only:

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
