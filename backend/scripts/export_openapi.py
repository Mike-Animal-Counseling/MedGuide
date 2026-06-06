import json
from pathlib import Path

from app.main import create_app


def main() -> None:
    output_path = Path("openapi.json")
    schema = create_app().openapi()
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Exported OpenAPI schema to {output_path}")


if __name__ == "__main__":
    main()
