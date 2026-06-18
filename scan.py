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


def _git(folder, *args):
    return subprocess.run(["git", "-C", str(folder), *args],
                          capture_output=True, text=True)


def _normalize_remote(url):
    url = (url or "").strip()
    if not url:
        return None
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url[len("git@github.com:"):]
    if url.endswith(".git"):
        url = url[:-4]
    return url


def get_git_info(folder):
    inside = _git(folder, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return {"last_commit": None, "repo_url": None}
    date = _git(folder, "log", "-1", "--format=%cs")
    last_commit = date.stdout.strip() or None
    remote = _git(folder, "remote", "get-url", "origin")
    repo_url = _normalize_remote(remote.stdout) if remote.returncode == 0 else None
    return {"last_commit": last_commit, "repo_url": repo_url}


DOC_FILES = ["README.md", "README.MD", "Readme.md", "readme.md", "CLAUDE.md"]


def doc_fingerprint(folder):
    folder = Path(folder)
    times = [(folder / name).stat().st_mtime for name in DOC_FILES if (folder / name).exists()]
    return max(times) if times else 0.0


def build_links(repo_url, override):
    return {"repo": repo_url, "live": override.get("live")}


def infer_status(last_commit, links, override, today=None):
    if override.get("status"):
        return override["status"]
    if links.get("live"):
        return "live"
    if last_commit:
        if today is None:
            today = datetime.now(timezone.utc).date()
        age = (today - datetime.strptime(last_commit, "%Y-%m-%d").date()).days
        if age > 90:
            return "paused"
    return "wip"


def build_project(disc):
    folder = Path(disc["path"])
    override = disc["override"]
    git = get_git_info(folder)
    links = build_links(git["repo_url"], override)
    status = infer_status(git["last_commit"], links, override)
    tags = list(override.get("tags", [])) or detect_tags(folder)
    return {
        "name": disc["name"],
        "display_name": override.get("display_name", disc["name"]),
        "tool": disc["tool"],
        "summary": "",
        "tags": tags,
        "status": status,
        "last_commit": git["last_commit"],
        "links": links,
        "fingerprint": doc_fingerprint(folder),
        "summary_stale": True,
    }


def merge_projects(new_list, existing):
    by_name = {p["name"]: p for p in existing.get("projects", [])}
    merged = []
    for p in new_list:
        old = by_name.get(p["name"])
        if old and old.get("summary"):
            p["summary"] = old["summary"]
            p["summary_stale"] = old.get("fingerprint") != p["fingerprint"]
        merged.append(p)
    return merged


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
