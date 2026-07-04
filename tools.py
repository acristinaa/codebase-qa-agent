import re
import subprocess
from pathlib import Path

from search import search as vector_search

TARGET_DIR = "target_repo"


def search_code(query, k=5):
    """Semantic search over the codebase. Returns the top-k relevant chunks."""
    return vector_search(query, k=k)


def read_file(path, start_line=None, end_line=None):
    """Read a file (optionally a line range) from target_repo/.
    path is relative to target_repo/, e.g. 'src/flask/app.py'."""
    full_path = (Path(TARGET_DIR) / path).resolve()
    root = Path(TARGET_DIR).resolve()

    if root not in full_path.parents and full_path != root:
        return {"error": f"path escapes {TARGET_DIR}/, refusing to read"}
    if not full_path.exists():
        return {"error": f"file not found: {path}"}

    lines = full_path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = (start_line or 1) - 1
    end = end_line or len(lines)
    start = max(start, 0)
    end = min(end, len(lines))

    return {
        "path": path,
        "start_line": start + 1,
        "end_line": end,
        "content": "\n".join(lines[start:end]),
    }


def find_dependents(function_name, max_results=30):
    """find likely callers of a function/class: greps for the name being
    called or referenced, across all .py files in target_repo/.
    accepts either a bare name ('route') or a qualified one ('Scaffold.route') —
    qualified names are reduced to the last segment, since callers rarely
    write the class prefix."""
    bare_name = function_name.rsplit(".", 1)[-1]
    pattern = re.compile(rf"\b{re.escape(bare_name)}\b")
    root = Path(TARGET_DIR)
    matches = []

    for path in root.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line) and not line.strip().startswith(("def ", "class ")):
                matches.append({
                    "file": str(path.relative_to(root)),
                    "line": i,
                    "text": line.strip(),
                })
                if len(matches) >= max_results:
                    return matches
    return matches


def find_definition(name):
    """find where a function or class is defined, via grep for 'def name' /
    'class name'. Accepts either a bare name ('route') or a qualified one
    ('Scaffold.route') — qualified names are reduced to the last segment."""
    bare_name = name.rsplit(".", 1)[-1]
    root = Path(TARGET_DIR)
    pattern = re.compile(rf"^\s*(def|class)\s+{re.escape(bare_name)}\b")
    results = []

    for path in root.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if pattern.match(line):
                results.append({
                    "file": str(path.relative_to(root)),
                    "line": i,
                    "text": line.strip(),
                })
    return results


if __name__ == "__main__":
    # Quick manual smoke test — run: python tools.py
    print("=== search_code ===")
    for h in search_code("how is a route registered", k=3):
        print(h)

    print("\n=== find_definition('route') ===")
    for r in find_definition("route")[:5]:
        print(r)

    print("\n=== find_dependents('add_url_rule') ===")
    for r in find_dependents("add_url_rule")[:5]:
        print(r)

    print("\n=== read_file ===")
    defs = find_definition("route")
    if defs:
        f = defs[0]
        res = read_file(f["file"], f["line"], f["line"] + 10)
        print(res["content"])
