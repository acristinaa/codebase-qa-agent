import ast
import json
from pathlib import Path

TARGET_DIR = "target_repo"
OUTPUT_FILE = "chunks.json"
SKIP_DIRS = {".venv", "venv", "__pycache__", ".git", "build", "dist", "tests"}


def get_imports(tree):
    """Collect a file's top-level imports as readable strings, for context."""
    imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                imports.append(f"import {a.name}" + (f" as {a.asname}" if a.asname else ""))
        elif isinstance(node, ast.ImportFrom):
            names = ", ".join(a.name + (f" as {a.asname}" if a.asname else "") for a in node.names)
            imports.append(f"from {'.' * node.level}{node.module or ''} import {names}")
    return imports


def extract_chunks(path, repo_root):
    rel_path = str(Path(path).relative_to(repo_root))
    try:
        source = Path(path).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel_path)
    except (UnicodeDecodeError, SyntaxError, OSError):
        return []  # skip unreadable / non-parseable files instead of crashing

    imports = get_imports(tree)
    chunks = []

    def visit(node, prefix):
        for child in getattr(node, "body", []):
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            qualname = f"{prefix}{child.name}"
            kind = "class" if isinstance(child, ast.ClassDef) else ("method" if prefix else "function")
            chunks.append({
                "id": f"{rel_path}::{qualname}",
                "type": kind,
                "name": child.name,
                "qualname": qualname,
                "file": rel_path,
                "start_line": child.lineno,
                "end_line": getattr(child, "end_lineno", child.lineno),
                "docstring": ast.get_docstring(child),
                "source": ast.get_source_segment(source, child),
                "imports": imports,
            })
            if isinstance(child, ast.ClassDef):
                visit(child, prefix=f"{qualname}.")  # recurse for methods

    visit(tree, prefix="")
    return chunks


def main():
    repo_root = Path(TARGET_DIR).resolve()
    if not repo_root.exists():
        raise SystemExit(f"{TARGET_DIR}/ not found — clone a repo into it first.")

    py_files = [p for p in repo_root.rglob("*.py") if not SKIP_DIRS & set(p.parts)]
    all_chunks = []
    for path in py_files:
        all_chunks.extend(extract_chunks(path, repo_root))

    Path(OUTPUT_FILE).write_text(json.dumps(all_chunks, indent=2), encoding="utf-8")
    print(f"Parsed {len(py_files)} files → {len(all_chunks)} chunks → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()