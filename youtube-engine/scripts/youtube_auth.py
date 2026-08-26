from __future__ import annotations

import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

client_file = Path(os.getenv("YOUTUBE_CLIENT_SECRETS", "/app/secrets/client_secret.json"))
token_file = Path(os.getenv("YOUTUBE_TOKEN_FILE", "/app/secrets/youtube_token.json"))

if not client_file.exists():
    raise SystemExit(f"Missing OAuth client file: {client_file}")

flow = InstalledAppFlow.from_client_secrets_file(str(client_file), SCOPES)
creds = flow.run_local_server(port=0, open_browser=False)
token_file.parent.mkdir(parents=True, exist_ok=True)
token_file.write_text(creds.to_json(), encoding="utf-8")
print(f"Saved YouTube OAuth token to {token_file}")
