# 포트폴리오 대시보드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 두 위치의 프로젝트 폴더를 스캔해 메타데이터를 모으고, Claude가 채운 요약과 합쳐 `projects.json`을 만들고, 확정된 "빌드 로그/청사진 콘솔" 디자인이 그 데이터를 렌더하는 정적 대시보드를 GitHub Pages로 배포한다.

**Architecture:** 데이터(`projects.json`)와 화면(`index.html`) 분리. 로컬 `scan.py`가 git·파일 메타를 수집하고 요약을 보존/갱신 표시하며 `projects.json`을 쓴다. `index.html`은 클라이언트 JS로 `projects.json`을 fetch해 카드를 렌더하고 필터링한다. Pages는 정적 파일만 서빙(빌드 단계 없음).

**Tech Stack:** Python 3 표준 라이브러리(pathlib, subprocess, json, datetime) + pytest. 프런트엔드는 프레임워크 없는 HTML/CSS/JS(확정 디자인 그대로).

---

## File Structure

```
Portfolio/
├─ index.html             # 확정 디자인 + 데이터 렌더 JS
├─ projects.json          # 산출 데이터 (scan.py가 씀)
├─ projects.config.json   # 소스 경로 2곳 + 제외/오버라이드
├─ scan.py                # 로컬 스캔·메타수집·머지
├─ tests/test_scan.py     # scan.py 단위 테스트
├─ .gitignore
├─ README.md
└─ docs/superpowers/...    # spec, plan (이미 존재)
```

- `scan.py`는 순수 함수들(discover/detect/git/status/merge) + `main()`으로 구성해 테스트 가능하게 한다.
- 프런트엔드는 단일 `index.html`(디자인이 단일 파일로 확정됨)을 유지하되 정적 카드를 JS 렌더로 교체한다.

---

## Task 1: 리포지토리 골격 (config·gitignore·README)

**Files:**
- Create: `Portfolio/projects.config.json`
- Create: `Portfolio/.gitignore`
- Create: `Portfolio/README.md`

- [ ] **Step 1: `projects.config.json` 작성**

```json
{
  "sources": [
    { "path": "C:/Users/ljk90/OneDrive/Desktop/Papa Jun Kyu", "tool": "Claude Code" },
    { "path": "C:/Users/ljk90/OneDrive/문서/Claude/Projects", "tool": "Cowork" }
  ],
  "exclude": [
    "Portfolio", "Feedback_SW", "26년도 식단", "색깔놀이_그림",
    "뭐든지_app", "뭐든지_parent_app", "뭐든지_통합"
  ],
  "overrides": {
    "뭐든지_Claude_Code": { "display_name": "뭐든지 앱" },
    "시간표_관리": { "live": "https://example.github.io/schedule", "status": "live" },
    "Play_Archive": { "live": "https://example.github.io/play-archive", "status": "live" }
  }
}
```
> `live` URL은 실제 Pages 주소를 아는 대로 채운다(모르면 그 항목 생략). 자동으로 못 거르는 폴더가 보이면 `exclude`에 추가.

- [ ] **Step 2: `.gitignore` 작성**

```gitignore
_workspace/
.superpowers/
__pycache__/
*.pyc
.pytest_cache/
.claude/settings.local.json
```

- [ ] **Step 3: `README.md` 작성**

```markdown
# 원준 아빠의 프로젝트 대시보드

Claude Code·Cowork로 만든 프로젝트를 한곳에 모으는 개인 대시보드.

## 갱신 방법
1. `python scan.py` — 폴더를 스캔해 `projects.json`의 메타데이터 갱신, 요약이 필요한 프로젝트를 출력.
2. 출력된 프로젝트의 요약을 Claude에게 채워달라고 요청(README/CLAUDE.md/코드를 읽고 한 줄 요약).
3. `git add -A && git commit && git push` — GitHub Pages에 자동 반영.

## 로컬 미리보기
`python -m http.server 8000` 실행 후 브라우저에서 http://localhost:8000 (파일 직접 열기는 fetch가 막혀 안 됨).
```

- [ ] **Step 4: Commit** (Task 11에서 `git init` 후 일괄 커밋하므로, 아직 git이 없으면 이 단계는 Task 11로 미룬다. git이 이미 있으면 아래 실행)

```bash
git add projects.config.json .gitignore README.md
git commit -m "chore: portfolio repo skeleton + config"
```

---

## Task 2: `scan.py` — 설정 로드와 프로젝트 발견

**Files:**
- Create: `Portfolio/scan.py`
- Test: `Portfolio/tests/test_scan.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_scan.py`:
```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py -v`
Expected: FAIL (`AttributeError: module 'scan' has no attribute 'discover_projects'`)

- [ ] **Step 3: 최소 구현**

`scan.py`:
```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scan.py tests/test_scan.py
git commit -m "feat(scan): discover projects from configured sources"
```

---

## Task 3: `scan.py` — 기술 태그 감지

**Files:**
- Modify: `Portfolio/scan.py`
- Test: `Portfolio/tests/test_scan.py`

- [ ] **Step 1: 실패하는 테스트 작성** (`tests/test_scan.py`에 추가)

```python
def test_detect_tags_by_file_markers(tmp_path):
    proj = tmp_path / "proj"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "app.py").write_text("print(1)", encoding="utf-8")
    (proj / "index.html").write_text("<html></html>", encoding="utf-8")
    (proj / ".git").mkdir()                      # 무시되어야 함
    (proj / ".git" / "x.py").write_text("", encoding="utf-8")
    tags = scan.detect_tags(proj)
    assert "Python" in tags and "Web" in tags
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py::test_detect_tags_by_file_markers -v`
Expected: FAIL (`no attribute 'detect_tags'`)

- [ ] **Step 3: 최소 구현** (`scan.py`에 추가)

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py::test_detect_tags_by_file_markers -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scan.py tests/test_scan.py
git commit -m "feat(scan): detect tech tags from file markers"
```

---

## Task 4: `scan.py` — 문서 핑거프린트 (요약 stale 판정용)

**Files:**
- Modify: `Portfolio/scan.py`
- Test: `Portfolio/tests/test_scan.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py::test_doc_fingerprint_changes_when_docs_change -v`
Expected: FAIL (`no attribute 'doc_fingerprint'`)

- [ ] **Step 3: 최소 구현** (`scan.py`에 추가)

```python
DOC_FILES = ["README.md", "README.MD", "Readme.md", "readme.md", "CLAUDE.md"]


def doc_fingerprint(folder):
    folder = Path(folder)
    times = [(folder / name).stat().st_mtime for name in DOC_FILES if (folder / name).exists()]
    return max(times) if times else 0.0
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py::test_doc_fingerprint_changes_when_docs_change -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scan.py tests/test_scan.py
git commit -m "feat(scan): doc fingerprint for summary staleness"
```

---

## Task 5: `scan.py` — git 메타데이터 (마지막 커밋·원격)

**Files:**
- Modify: `Portfolio/scan.py`
- Test: `Portfolio/tests/test_scan.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py -k git -v`
Expected: FAIL (`no attribute 'get_git_info'`)

- [ ] **Step 3: 최소 구현** (`scan.py`에 추가)

```python
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
```
> `%cs` = committer date, short ISO(YYYY-MM-DD). git 2.x 필요(설치돼 있음).

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py -k git -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scan.py tests/test_scan.py
git commit -m "feat(scan): collect git last-commit and normalized remote"
```

---

## Task 6: `scan.py` — 링크 조립과 상태 추정

**Files:**
- Modify: `Portfolio/scan.py`
- Test: `Portfolio/tests/test_scan.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from datetime import date

def test_build_links_prefers_remote_and_override_live():
    links = scan.build_links("https://github.com/u/r", {"live": "https://x.io"})
    assert links == {"repo": "https://github.com/u/r", "live": "https://x.io"}
    assert scan.build_links(None, {}) == {"repo": None, "live": None}

def test_infer_status_rules():
    today = date(2026, 6, 18)
    # override 우선
    assert scan.infer_status("2026-06-18", {"live": None}, {"status": "paused"}, today) == "paused"
    # live 링크 있으면 live
    assert scan.infer_status("2026-06-18", {"live": "https://x"}, {}, today) == "live"
    # 90일 초과 무커밋 → paused
    assert scan.infer_status("2026-01-01", {"live": None}, {}, today) == "paused"
    # 최근 커밋 → wip
    assert scan.infer_status("2026-06-10", {"live": None}, {}, today) == "wip"
    # git 없음(None) → wip
    assert scan.infer_status(None, {"live": None}, {}, today) == "wip"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py -k "links or status" -v`
Expected: FAIL (`no attribute 'build_links'`)

- [ ] **Step 3: 최소 구현** (`scan.py`에 추가)

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py -k "links or status" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scan.py tests/test_scan.py
git commit -m "feat(scan): assemble links and infer project status"
```

---

## Task 7: `scan.py` — 프로젝트 조립과 머지(요약 보존)

**Files:**
- Modify: `Portfolio/scan.py`
- Test: `Portfolio/tests/test_scan.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_merge_preserves_summary_when_fingerprint_unchanged():
    new = [{"name": "A", "summary": "", "fingerprint": 10.0, "summary_stale": True}]
    existing = {"projects": [{"name": "A", "summary": "기존 요약", "fingerprint": 10.0}]}
    merged = scan.merge_projects(new, existing)
    assert merged[0]["summary"] == "기존 요약"
    assert merged[0]["summary_stale"] is False

def test_merge_marks_stale_when_fingerprint_changed():
    new = [{"name": "A", "summary": "", "fingerprint": 20.0, "summary_stale": True}]
    existing = {"projects": [{"name": "A", "summary": "기존", "fingerprint": 10.0}]}
    merged = scan.merge_projects(new, existing)
    assert merged[0]["summary"] == "기존"          # 텍스트는 보존
    assert merged[0]["summary_stale"] is True       # 변경됨 → 갱신 필요

def test_merge_new_project_is_stale():
    new = [{"name": "B", "summary": "", "fingerprint": 5.0, "summary_stale": True}]
    merged = scan.merge_projects(new, {"projects": []})
    assert merged[0]["summary_stale"] is True
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py -k merge -v`
Expected: FAIL (`no attribute 'merge_projects'`)

- [ ] **Step 3: 최소 구현** (`scan.py`에 추가)

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py -k merge -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scan.py tests/test_scan.py
git commit -m "feat(scan): build project records and merge preserving summaries"
```

---

## Task 8: `scan.py` — CLI 진입점(`main`)과 `projects.json` 쓰기

**Files:**
- Modify: `Portfolio/scan.py`
- Test: `Portfolio/tests/test_scan.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_run_scan_writes_projects_json(tmp_path, monkeypatch):
    cc = tmp_path / "cc"; (cc / "Gamma").mkdir(parents=True)
    (cc / "Gamma" / "main.py").write_text("print(1)", encoding="utf-8")
    config = {"sources": [{"path": str(cc), "tool": "Claude Code"}],
              "exclude": [], "overrides": {}}
    out = tmp_path / "projects.json"
    result = scan.run_scan(config, out)               # 순수 함수형 진입점
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "generated_at" in data
    names = [p["name"] for p in data["projects"]]
    assert names == ["Gamma"]
    assert "Python" in data["projects"][0]["tags"]
    assert result["stale"] == ["Gamma"]               # 요약 필요 목록 반환
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py -k run_scan -v`
Expected: FAIL (`no attribute 'run_scan'`)

- [ ] **Step 3: 최소 구현** (`scan.py`에 추가)

```python
def run_scan(config, output_path):
    existing = {}
    if Path(output_path).exists():
        existing = json.loads(Path(output_path).read_text(encoding="utf-8"))
    disc = discover_projects(config)
    new_list = [build_project(d) for d in disc]
    merged = merge_projects(new_list, existing)
    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "projects": merged,
    }
    Path(output_path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    stale = [p["name"] for p in merged if p["summary_stale"]]
    return {"total": len(merged), "stale": stale}


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
```

- [ ] **Step 4: 테스트 통과 + 전체 스위트 확인**

Run: `cd Portfolio && python -m pytest tests/test_scan.py -v`
Expected: 전부 PASS

- [ ] **Step 5: Commit**

```bash
git add scan.py tests/test_scan.py
git commit -m "feat(scan): run_scan entrypoint writes projects.json + stale report"
```

---

## Task 9: `index.html` — 데이터 기반 렌더 + 필터

**Files:**
- Create: `Portfolio/index.html` (확정 디자인 복사 후 수정)
- Modify: `Portfolio/index.html`

- [ ] **Step 1: 확정 디자인을 복사**

```bash
cp "_workspace/02_design/index.html" "index.html"
```

- [ ] **Step 2: 헤더 통계에 id 부여** — `index.html`의 `.stats` 블록을 아래로 교체(숫자/날짜를 JS가 채우도록 id 추가, 초기값은 비움)

```html
  <div class="stats">
    <div class="stat"><span class="stat__num" id="statTotal">–</span><span class="stat__label">projects</span></div>
    <div class="stat"><span class="stat__num stat__num--wip" id="statWip">–</span><span class="stat__label">in-progress</span></div>
    <div class="stat"><span class="stat__num stat__num--live" id="statLive">–</span><span class="stat__label">live</span></div>
    <div class="stat"><span class="stat__num" id="statUpdated">–</span><span class="stat__label">last update</span></div>
  </div>
```

- [ ] **Step 3: 정적 카드를 빈 컨테이너로 교체** — `<section class="grid" ...> ... </section>`의 **내부 8개 `<article>`를 모두 삭제**하고 비워둔다(클래스·aria 유지). 결과:

```html
  <section class="grid" id="grid" aria-label="프로젝트 목록"></section>
```

- [ ] **Step 4: 기존 인라인 필터 스크립트를 렌더+필터 스크립트로 교체** — `</body>` 직전의 `<script> ... </script>` 전체를 아래로 교체

```html
<script>
(function () {
  var STATUS_LABEL = { wip: "in-progress", live: "live", paused: "paused" };

  function relTime(iso) {
    if (!iso) return "no commits";
    var then = new Date(iso + "T00:00:00Z");
    var days = Math.floor((Date.now() - then.getTime()) / 86400000);
    if (days <= 0) return "today";
    if (days < 7) return days + "d ago";
    if (days < 30) return Math.floor(days / 7) + "w ago";
    if (days < 365) return Math.floor(days / 30) + "mo ago";
    return Math.floor(days / 365) + "y ago";
  }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function card(p) {
    var art = el("article", "card");
    art.dataset.tool = (p.tool || "").toLowerCase();
    art.dataset.status = p.status || "wip";

    var row = el("div", "card__statusrow");
    var st = el("span", "status status--" + (p.status || "wip"));
    st.appendChild(el("span", "dot"));
    st.appendChild(document.createTextNode(STATUS_LABEL[p.status] || p.status || ""));
    row.appendChild(st);
    row.appendChild(el("span", "tool-tag", (p.tool || "").toLowerCase()));
    art.appendChild(row);

    var body = el("div");
    body.appendChild(el("h2", "card__title", p.display_name || p.name));
    body.appendChild(el("p", "card__desc", p.summary || "요약 준비 중"));
    art.appendChild(body);

    var tags = el("div", "tags");
    (p.tags || []).forEach(function (t) { tags.appendChild(el("span", "tag", t)); });
    art.appendChild(tags);

    var foot = el("div", "card__foot");
    foot.appendChild(el("span", "log", "· last commit " + relTime(p.last_commit)));
    var links = el("div", "links");
    if (p.links && p.links.repo) {
      var a = el("a", "link", "git"); a.href = p.links.repo; a.target = "_blank"; a.rel = "noopener";
      links.appendChild(a);
    }
    if (p.links && p.links.live) {
      var b = el("a", "link", "live↗"); b.href = p.links.live; b.target = "_blank"; b.rel = "noopener";
      links.appendChild(b);
    }
    foot.appendChild(links);
    art.appendChild(foot);
    return art;
  }

  var state = { tool: "all", statuses: [] };  // tool: single; statuses: multi (empty=all)

  function applyFilters() {
    document.querySelectorAll(".card").forEach(function (c) {
      var okTool = state.tool === "all" || c.dataset.tool === state.tool;
      var okStatus = state.statuses.length === 0 || state.statuses.indexOf(c.dataset.status) !== -1;
      c.style.display = (okTool && okStatus) ? "" : "none";
    });
  }

  var STATUS_FROM_CHIP = { "in-progress": "wip", "live": "live", "paused": "paused" };

  function wireFilters() {
    var groups = document.querySelectorAll(".filter-group");
    // group[0] = 구분(tool) 단일선택, group[1] = 상태 다중토글
    groups[0].addEventListener("click", function (e) {
      var chip = e.target.closest(".chip"); if (!chip) return;
      groups[0].querySelectorAll(".chip").forEach(function (c) {
        c.setAttribute("aria-pressed", c === chip ? "true" : "false");
      });
      var label = chip.textContent.trim();
      state.tool = label === "all" ? "all" : label;  // "claude code" / "cowork"
      applyFilters();
    });
    if (groups[1]) groups[1].addEventListener("click", function (e) {
      var chip = e.target.closest(".chip"); if (!chip) return;
      var pressed = chip.getAttribute("aria-pressed") === "true";
      chip.setAttribute("aria-pressed", pressed ? "false" : "true");
      var status = STATUS_FROM_CHIP[chip.textContent.trim()];
      var i = state.statuses.indexOf(status);
      if (i === -1) state.statuses.push(status); else state.statuses.splice(i, 1);
      applyFilters();
    });
  }

  function renderStats(data) {
    var ps = data.projects || [];
    document.getElementById("statTotal").textContent = ps.length;
    document.getElementById("statWip").textContent = ps.filter(function (p) { return p.status === "wip"; }).length;
    document.getElementById("statLive").textContent = ps.filter(function (p) { return p.status === "live"; }).length;
    document.getElementById("statUpdated").textContent = data.generated_at || "–";
  }

  function render(data) {
    renderStats(data);
    var grid = document.getElementById("grid");
    grid.innerHTML = "";
    (data.projects || []).slice().sort(function (a, b) {
      return (b.last_commit || "").localeCompare(a.last_commit || "");
    }).forEach(function (p) { grid.appendChild(card(p)); });
    wireFilters();
    applyFilters();
  }

  // 테마 토글(확정 디자인 동작 유지)
  var toggle = document.getElementById("themeToggle");
  if (toggle) toggle.addEventListener("click", function () {
    var dark = document.documentElement.getAttribute("data-theme") !== "light";
    document.documentElement.setAttribute("data-theme", dark ? "light" : "dark");
    toggle.textContent = dark ? "// dark" : "// light";
  });

  fetch("projects.json")
    .then(function (r) { return r.json(); })
    .then(render)
    .catch(function (e) {
      document.getElementById("grid").innerHTML =
        '<p class="card__desc">projects.json을 불러오지 못했습니다. `python -m http.server`로 실행했는지 확인하세요.</p>';
      console.error(e);
    });
})();
</script>
```
> 테마 토글 코드는 확정 디자인의 기존 동작과 같다. 확정 파일의 토글 구현이 `data-theme` 속성 방식과 다르면, 위 toggle 블록을 빼고 기존 토글 코드를 그대로 둔 채 fetch/render 부분만 추가한다.

- [ ] **Step 5: 픽스처로 로컬 검증**

`projects.json`(임시 픽스처) 생성:
```json
{
  "generated_at": "2026-06-18",
  "projects": [
    {"name":"Vision_FB_SW","display_name":"Vision_FB_SW","tool":"Claude Code","summary":"설비 비전 검사 결과를 PPTX 리포트로 자동 생성.","tags":["Python","PPTX"],"status":"wip","last_commit":"2026-06-16","links":{"repo":"https://github.com/u/vision","live":null}},
    {"name":"시간표_관리","display_name":"시간표_관리","tool":"Cowork","summary":"주간 시간표 편집·공유 웹앱.","tags":["Web","JS"],"status":"live","last_commit":"2026-06-15","links":{"repo":"https://github.com/u/sched","live":"https://u.github.io/sched"}},
    {"name":"image-classifier","display_name":"image-classifier","tool":"Claude Code","summary":"이미지 자동 분류 CLI.","tags":["Python"],"status":"paused","last_commit":"2026-03-01","links":{"repo":null,"live":null}}
  ]
}
```

Run: `cd Portfolio && python -m http.server 8000`
브라우저에서 http://localhost:8000 열기.
Expected:
- 카드 3개가 청사진 콘솔 디자인으로 렌더(최근 커밋순 정렬).
- 상태 뱃지 색(wip/live/paused), 통계가 3/1/1/2026-06-18.
- "claude code"/"cowork" 칩 클릭 시 필터, 상태 칩 토글 필터 동작.
- image-classifier는 링크 없음(로컬 전용). 콘솔 에러 없음.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "feat(ui): render dashboard cards and filters from projects.json"
```

---

## Task 10: 실제 `projects.json` 생성 (스캔 + Claude 요약)

**Files:**
- Modify: `Portfolio/projects.json` (실데이터로 교체)

- [ ] **Step 1: 픽스처 제거 후 실제 스캔**

Run: `cd Portfolio && python scan.py`
Expected: `N projects scanned -> projects.json` + 요약 필요 목록 출력. (Task 9 Step 5의 픽스처 projects.json은 이 실행이 덮어쓴다.)

- [ ] **Step 2: Claude 요약 채우기** (Claude에게 요청)

출력된 stale 목록의 각 프로젝트에 대해 Claude가 해당 폴더(README/CLAUDE.md/주요 코드)를 읽고 `projects.json`의 `summary`를 한 줄(공개 URL이라 민감정보 없이, 가족 프로젝트는 톤 순화)로 채우고 `summary_stale`을 `false`로 바꾼다.
> 자동화 아님. `scan.py`가 메타를, Claude가 요약을 담당하는 분업(spec 섹션 7).

- [ ] **Step 3: 로컬 확인**

Run: `cd Portfolio && python -m http.server 8000` → http://localhost:8000
Expected: 실제 14개 내외 프로젝트가 요약과 함께 렌더, 필터·통계 정상.

- [ ] **Step 4: Commit**

```bash
git add projects.json
git commit -m "data: initial projects.json with summaries"
```

---

## Task 11: 배포 — git init + GitHub + Pages

**Files:** (없음 — 운영 절차)

- [ ] **Step 1: git 저장소 초기화** (아직 git이 아니면)

```bash
cd "Portfolio"
git init -b main
git add -A
git commit -m "feat: portfolio dashboard (scan + data-driven static site)"
```

- [ ] **Step 2: GitHub 원격 생성·푸시** (gh CLI 있으면)

```bash
gh repo create papa-junkyu-portfolio --public --source=. --remote=origin --push
```
gh가 없으면: GitHub 웹에서 빈 repo 생성 후
```bash
git remote add origin https://github.com/<계정>/papa-junkyu-portfolio.git
git push -u origin main
```

- [ ] **Step 3: GitHub Pages 활성화** (GitHub 웹 — 사용자 수행)

Repo → Settings → Pages → Source = `Deploy from a branch`, Branch = `main` / `/ (root)` → Save.
1~2분 후 `https://<계정>.github.io/papa-junkyu-portfolio/` 접속.
Expected: 모바일·데스크톱에서 대시보드가 뜨고 `projects.json`을 정상 로드.

- [ ] **Step 4: live URL을 config에 반영(선택)**

Pages 주소가 확정되면, Pages를 쓰는 프로젝트들의 `projects.config.json` `overrides[*].live`를 실제 주소로 갱신 → `python scan.py` → 커밋·푸시.

---

## Self-Review 메모
- spec 섹션 1~10 전부 태스크로 커버(스캔/메타/요약분업/링크규칙/디자인적용/배포·프라이버시). 섹션 11(YAGNI)·12(미해결)는 비구현 항목으로 의도적 제외.
- 함수명 일관성 확인: `discover_projects/detect_tags/doc_fingerprint/get_git_info/build_links/infer_status/build_project/merge_projects/run_scan/main` — 태스크 간 동일하게 사용.
- 프런트엔드 클래스명은 확정 디자인(`card/card__statusrow/status status--*/tool-tag/card__title/card__desc/tags/tag/card__foot/log/links/link/filter-group/chip/stat__num`)과 일치.
- 로컬 전용 프로젝트 링크 없음 규칙: `build_links`가 repo/live 둘 다 None → 카드 JS가 링크 미생성으로 반영.
