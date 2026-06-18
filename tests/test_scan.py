import json
from pathlib import Path
import scan

def _make_sources(tmp_path):
    cc = tmp_path / "cc"; cw = tmp_path / "cw"
    (cc / "Alpha").mkdir(parents=True); (cc / "Portfolio").mkdir()
    (cw / "Beta").mkdir(parents=True)
    (cc / "notafolder.txt").write_text("x", encoding="utf-8")
    return {
        "sources": [
            {"path": str(cc), "tool": "Claude Code"},
            {"path": str(cw), "tool": "Cowork"},
        ],
        "exclude": ["Portfolio"],
        "overrides": {"Beta": {"display_name": "베타"}},
    }

def test_discover_projects_lists_dirs_applies_exclude_and_tool(tmp_path):
    config = _make_sources(tmp_path)
    found = scan.discover_projects(config)
    names = {p["name"]: p for p in found}
    assert set(names) == {"Alpha", "Beta"}          # Portfolio excluded, txt ignored
    assert names["Alpha"]["tool"] == "Claude Code"
    assert names["Beta"]["tool"] == "Cowork"
    assert names["Beta"]["override"] == {"display_name": "베타"}

def test_detect_tags_by_file_markers(tmp_path):
    proj = tmp_path / "proj"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "app.py").write_text("print(1)", encoding="utf-8")
    (proj / "index.html").write_text("<html></html>", encoding="utf-8")
    (proj / ".git").mkdir()                      # 무시되어야 함
    (proj / ".git" / "x.py").write_text("", encoding="utf-8")
    tags = scan.detect_tags(proj)
    assert "Python" in tags and "Web" in tags

def test_doc_fingerprint_changes_when_docs_change(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    assert scan.doc_fingerprint(proj) == 0.0          # 문서 없음
    readme = proj / "README.md"
    readme.write_text("v1", encoding="utf-8")
    fp1 = scan.doc_fingerprint(proj)
    assert fp1 > 0.0
    import os, time
    future = time.time() + 100
    os.utime(readme, (future, future))
    assert scan.doc_fingerprint(proj) > fp1

def _init_git_repo(path, remote=None):
    import subprocess
    def g(*a): subprocess.run(["git", "-C", str(path), *a], check=True,
                              capture_output=True, text=True)
    g("init", "-q")
    g("config", "user.email", "t@t.t"); g("config", "user.name", "t")
    (path / "f.txt").write_text("x", encoding="utf-8")
    g("add", "-A"); g("commit", "-q", "-m", "init")
    if remote:
        g("remote", "add", "origin", remote)

def test_get_git_info_reads_commit_and_normalizes_ssh_remote(tmp_path):
    proj = tmp_path / "repo"; proj.mkdir()
    _init_git_repo(proj, remote="git@github.com:user/repo.git")
    info = scan.get_git_info(proj)
    assert info["last_commit"] is not None and len(info["last_commit"]) == 10  # YYYY-MM-DD
    assert info["repo_url"] == "https://github.com/user/repo"

def test_get_git_info_returns_none_for_non_repo(tmp_path):
    proj = tmp_path / "plain"; proj.mkdir()
    info = scan.get_git_info(proj)
    assert info == {"last_commit": None, "repo_url": None}
