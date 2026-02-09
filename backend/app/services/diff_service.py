import difflib


def generate_diff(text_a: str, text_b: str) -> dict:
    """Generate a unified diff between two texts."""
    lines_a = text_a.splitlines(keepends=True)
    lines_b = text_b.splitlines(keepends=True)

    diff = list(difflib.unified_diff(lines_a, lines_b, fromfile="Model A", tofile="Model B"))
    return {
        "unified_diff": "".join(diff),
        "lines_a": len(lines_a),
        "lines_b": len(lines_b),
    }
