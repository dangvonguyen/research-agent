import json
from pathlib import Path


def load_json_data(filepath) -> dict:
    """Load JSON data from a file."""
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def save_output(
    output_dir,
    response,
    type_name: str,
    json_idx: int,
    file_name: str | None = None,
    file_ext: str = "json",
) -> None:
    output_dir = Path(output_dir) / type_name / str(json_idx)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = (
        output_dir / f"{str(json_idx) if file_name is None else file_name}.{file_ext}"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        if file_ext == "txt":
            f.write(response)
        else:
            json.dump(response, f, ensure_ascii=False, indent=2)
