from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

# Allow this script to be executed directly from youtube-engine/scripts/ while
# still importing the project package from youtube-engine/.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from worker.pipeline import Pipeline


def main() -> None:
    job_id = str(uuid.uuid4())
    result = Pipeline().run(job_id=job_id)
    print(json.dumps({"job_id": job_id, **result}, indent=2))


if __name__ == "__main__":
    main()
