"""Write the API's OpenAPI schema to a file (default: frontend/lib/api/openapi.json).

The frontend's TypeScript types are generated from this file, so CI regenerates it and
fails when the committed copy has drifted from the Pydantic models.
"""

import json
import sys
from pathlib import Path

from piscope_api.main import create_app

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = REPO_ROOT / "frontend" / "lib" / "api" / "openapi.json"


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TARGET
    schema = create_app().openapi()
    target.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
