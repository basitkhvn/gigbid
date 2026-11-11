"""Write the FastAPI OpenAPI schema to apps/web/openapi.json (input of `npm run gen:api`)."""
import json
import os
from pathlib import Path

os.environ.setdefault("MODEL_PROFILE", "offline")
from apps.api.main import app  # noqa: E402

out = Path(__file__).resolve().parent.parent / "web" / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=1))
print("wrote", out)
