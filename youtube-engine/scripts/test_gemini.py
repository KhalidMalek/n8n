from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from google import genai


def main() -> int:
    load_dotenv()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-3.7-flash").strip()

    if not key:
        print("FAIL: GEMINI_API_KEY is missing from .env")
        return 1

    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: AUTOTUBE_GEMINI_OK",
        )
        text = (response.text or "").strip()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: Gemini request failed using model {model}")
        print(f"Error: {exc}")
        return 2

    if "AUTOTUBE_GEMINI_OK" not in text:
        print(f"FAIL: Gemini responded, but test response was unexpected: {text[:200]!r}")
        return 3

    print(f"SUCCESS: Gemini API connected ({model})")
    print("API key loaded securely from .env and was not displayed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
