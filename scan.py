import json
import os
import subprocess
import tempfile
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
                          capture_output=True, text=True, encoding="utf-8")


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
    none = {"last_commit": None, "repo_url": None}
    top = _git(folder, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        return none
    toplevel = top.stdout.strip()
    if not toplevel:
        return none
    # 부모 디렉토리가 repo일 때 하위 폴더가 부모 정보를 물려받지 않도록,
    # 해당 폴더가 repo 루트일 때만 git 정보를 반환한다.
    if Path(toplevel).resolve() != Path(folder).resolve():
        return none
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


def build_manual(entry):
    # config의 manual 항목 — 로컬 폴더가 없는(채팅/원격 전용) 프로젝트를 직접 정의한다.
    name = entry["name"]
    summary = entry.get("summary", "")
    return {
        "name": name,
        "display_name": entry.get("display_name", name),
        "tool": entry.get("tool", "Cowork"),
        "summary": summary,
        "tags": list(entry.get("tags", [])),
        "status": entry.get("status", "wip"),
        "last_commit": entry.get("last_commit"),
        "links": {"repo": entry.get("repo"), "live": entry.get("live")},
        "fingerprint": 0.0,
        "summary_stale": not summary,
    }


def merge_projects(new_list, existing):
    by_name = {p["name"]: p for p in existing.get("projects", [])}
    merged = []
    for p in new_list:
        old = by_name.get(p["name"])
        # 새 레코드에 요약이 없을 때만 이전 요약을 보존한다.
        # (manual 항목은 config가 요약의 출처이므로 덮어쓰지 않는다.)
        if old and old.get("summary") and not p.get("summary"):
            p["summary"] = old["summary"]
            p["summary_stale"] = old.get("fingerprint") != p["fingerprint"]
        merged.append(p)
    return merged


def discover_projects(config):
    exclude = set(config.get("exclude", []))
    overrides = config.get("overrides", {})
    projects = []
    seen = set()
    for source in config["sources"]:
        base = Path(source["path"])
        if not base.exists():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name in exclude:
                continue
            if child.name in seen:
                print(f"warning: duplicate project name '{child.name}' "
                      f"({child}) skipped — already found in another source.")
                continue
            seen.add(child.name)
            projects.append({
                "name": child.name,
                "path": str(child),
                "tool": source["tool"],
                "override": overrides.get(child.name, {}),
            })
    return projects


def run_scan(config, output_path):
    output_path = Path(output_path)
    existing = {}
    if output_path.exists():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"warning: {output_path.name} is not valid JSON ({e}); "
                  f"starting fresh.")
            existing = {}
    disc = discover_projects(config)
    new_list = [build_project(d) for d in disc]
    new_list += [build_manual(m) for m in config.get("manual", [])]
    merged = merge_projects(new_list, existing)
    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "projects": merged,
    }
    _atomic_write(output_path, json.dumps(data, ensure_ascii=False, indent=2))
    stale = [p["name"] for p in merged if p["summary_stale"]]
    return {"total": len(merged), "stale": stale}


def _atomic_write(path, text):
    # 임시 파일에 쓴 뒤 os.replace로 교체해 중간 중단 시 손상을 막는다.
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    result = run_scan(config, OUTPUT_PATH)
    print(f"{result['total']} projects scanned -> {OUTPUT_PATH.name}")
    if result["stale"]:
        print(f"{len(result['stale'])} need summaries (Claude에게 요청): {result['stale']}")
    else:
        print("all summaries up to date.")


if __name__ == "__main__":
    main()
