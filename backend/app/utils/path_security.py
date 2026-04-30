from pathlib import Path


def resolve_path_within(base_dir: str, child_path: str) -> Path | None:
    base = Path(base_dir).resolve()
    candidate = (base / child_path).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    return candidate
