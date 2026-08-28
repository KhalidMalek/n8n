from __future__ import annotations

import json
import uuid

from worker.pipeline import Pipeline


def main() -> None:
    job_id = str(uuid.uuid4())
    result = Pipeline().run(job_id=job_id)
    print(json.dumps({"job_id": job_id, **result}, indent=2))


if __name__ == "__main__":
    main()
