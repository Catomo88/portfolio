import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

CONFIG_PATH = Path(__file__).parent / "projects.config.json"
OUTPUT_PATH = Path(__file__).parent / "projects.json"


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
