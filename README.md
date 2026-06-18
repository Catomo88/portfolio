# 원준 아빠의 프로젝트 대시보드

Claude Code·Cowork로 만든 프로젝트를 한곳에 모으는 개인 대시보드. "빌드 로그 / 청사진 콘솔" 디자인.

## 갱신 방법
1. `python scan.py` — 폴더를 스캔해 `projects.json`의 메타데이터(도구·git 커밋·기술 태그·상태·링크)를 갱신하고, 요약이 필요한 프로젝트를 출력.
2. 출력된 프로젝트의 요약을 Claude에게 채워달라고 요청(README/CLAUDE.md/코드를 읽고 한 줄 요약 → `projects.json`의 `summary`).
3. `git add -A && git commit && git push` — GitHub Pages에 자동 반영.

## 로컬 미리보기
```
python -m http.server 8000
```
브라우저에서 http://localhost:8000 (파일을 직접 열면 `fetch`가 막혀 카드가 안 나옵니다).

## 구조
- `index.html` — 디자인 + projects.json을 fetch해 카드 렌더·필터링하는 JS.
- `projects.json` — 데이터(자동 메타 + Claude 요약). `scan.py`가 씀.
- `projects.config.json` — 소스 경로 2곳 + 제외/오버라이드.
- `scan.py` — 로컬 스캔·메타 수집·요약 보존 머지.
- `tests/` — `scan.py` 단위 테스트 (`python -m pytest`).

## 설정 (`projects.config.json`)
- `sources`: 스캔할 폴더 경로 + 도구 라벨.
- `exclude`: 카드로 안 만들 폴더명.
- `overrides`: 프로젝트별 `display_name` / `status` / `live`(라이브 URL) / `tags` 덮어쓰기.
