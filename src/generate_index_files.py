import json
import sys
from pathlib import Path

CATEGORIES = [
    "language-packs",
    "reference-formats",
    "translations",
]

ROOT_DIR = Path.joinpath(Path(__file__).parent.parent.parent,"biblens-data")

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_index_for_category(root_dir: Path, category: str) -> None:
    category_dir = root_dir / "resources" / category

    if not category_dir.exists():
        print(f"SKIP  {category} (directory not found)")
        return

    items = []

    for file_path in sorted(category_dir.glob("*.json")):
        if file_path.name == "index.json":
            continue

        data = load_json(file_path)

        item = {
            "id": data["id"],
            "displayName": data.get("displayName") or data["name"],
            "lang": data["lang"],
            "path": f"resources/{category}/{file_path.name}",
        }

        items.append(item)

    index_data = {
        "formatVersion": 1,
        "type": category,
        "items": items,
    }

    out_path = category_dir / "index.json"
    out_path.write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"OK   {category} -> {out_path}")


def main() -> None:

    root_dir = ROOT_DIR

    for category in CATEGORIES:
        build_index_for_category(root_dir, category)


if __name__ == "__main__":
    main()