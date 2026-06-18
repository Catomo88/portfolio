import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

CONFIG_PATH = Path(__file__).parent / "projects.config.json"
OUTPUT_PATH = Path(__file__).parent / "projects.json"


SKIP_DIRS = {".git", "node_modules", "__pycache__", ".superpowers", "_workspace"}


def _iter_files(folder, max_depth=3):
    folder = Path(folder)
    base = len(folder.parts)
    for p in folder.rglob("*"):
        rel_parts = p.parts[base:]
        if any(part in SKIP_DIRS or part.startswith(".") for part in rel_parts):
            continue
        if len(rel_parts) > max_depth:
            continue
        if p.is_file():
            yield p


def detect_tags(folder):
    files = list(_iter_files(folder))
    names = {f.name for f in files}
    suffixes = {f.suffix.lower() for f in files}
    tags = []

    def add(t):
        if t not in tags:
            tags.append(t)

    if ".py" in suffixes:
        add("Python")
    if "_config.yml" in names or "Gemfile" in names:
        add("Jekyll")
    if ".kt" in suffixes or "build.gradle" in names:
        add("Android")
    if "pubspec.yaml" in names:
        add("Flutter")
    if ".ipynb" in suffixes:
        add("Notebook")
    if "index.html" in names:
        add("Web")
    return tags


DOC_FILES = ["README.md", "README.MD", "Readme.md", "readme.md", "CLAUDE.md"]


def doc_fingerprint(folder):
    folder = Path(folder)
    times = [(folder / name).stat().st_mtime for name in DOC_FILES if (folder / name).exists()]
    return max(times) if times else 0.0


def discover_projects(config):
    exclude = set(config.get("exclude", []))
    overrides = config.get("overrides", {})
    projects = []
    for source in config["sources"]:
        base = Path(source["path"])
        if not base.exists():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name in exclude:
                continue
            projects.append({
                "name": child.name,
                "path": str(child),
                "tool": source["tool"],
                "override": overrides.get(child.name, {}),
            })
    return projects
