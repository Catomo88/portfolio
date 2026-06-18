# 원준 아빠의 프로젝트 대시보드 — 설계 문서

작성일: 2026-06-18

## 1. 개요 & 목표
Claude Code·Cowork로 만든 여러 프로젝트를 한 화면에 모으는 **개인용 프로젝트 대시보드**. 각 폴더의 README·CLAUDE.md·코드·git 이력을 읽어 **프로젝트 요약 카드를 자동 생성**한다. `Portfolio/` 폴더(별도 git 저장소)에 두고 GitHub Pages로 배포해 모바일에서도 본다.

**핵심 목표**
- 손으로 설명 안 해도 폴더만 읽으면 카드가 생성된다(Claude 지능형 요약).
- 모바일 우선. 공개 GitHub Pages URL로 어디서나 확인.
- 도구(Claude Code/Cowork) 무관하게 폴더만 읽으면 됨.

## 2. 아키텍처 — 3단계 + 클라이언트 렌더
```
[1] Claude 스캔 패스        [2] scan.py (로컬)            [3] 정적 호스팅
각 폴더 README/CLAUDE.md/  →  git·파일 메타 자동 수집     →  index.html이
코드 읽고 summary 작성        + Claude 요약 병합            projects.json을 fetch
        ↓                        ↓                          해 카드 렌더
   요약 텍스트              projects.json (최종 데이터)    GitHub Pages
```
- **데이터(`projects.json`)와 화면(`index.html`)을 분리.**
- 렌더는 클라이언트 JS가 `projects.json`을 fetch해서 수행 → Pages에서 빌드 단계 없이 동작. 필터 칩도 이 데이터로 작동.
- 로컬 메타 수집(git 등)은 Pages가 못 하므로 `scan.py`가 PC에서 담당.

## 3. 폴더 구조
```
Portfolio/
├─ index.html             # 확정 디자인. 카드는 JS가 projects.json에서 렌더
├─ projects.json          # 데이터: 자동 메타 + Claude 요약
├─ scan.py                # 로컬 실행: 두 소스 스캔 → 메타 수집 → projects.json 갱신
├─ projects.config.json   # 소스 경로 2곳 + 포함/제외 목록
├─ README.md
└─ .gitignore             # _workspace/, .superpowers/ 등 제외
```

## 4. 설정 — `projects.config.json`
```json
{
  "sources": [
    { "path": "C:/Users/ljk90/OneDrive/Desktop/Papa Jun Kyu", "tool": "Claude Code" },
    { "path": "C:/Users/ljk90/OneDrive/문서/Claude/Projects", "tool": "Cowork" }
  ],
  "exclude": ["Portfolio", "Feedback_SW", "26년도 식단", "색깔놀이_그림",
              "뭐든지_app", "뭐든지_parent_app", "뭐든지_통합"],
  "overrides": {
    "뭐든지_Claude_Code": { "display_name": "뭐든지 앱" }
  }
}
```
- 두 소스를 자동 발견하되 `exclude`로 비코드·덤프 폴더 제외.
- 뭐든지 앱 = `뭐든지_Claude_Code` 하나가 정본(데스크톱 zip 덤프 3개는 제외).

## 5. 데이터 — `projects.json` (항목 스키마)
```json
{
  "name": "Vision_FB_SW",
  "display_name": "Vision_FB_SW",
  "tool": "Claude Code",
  "summary": "설비 비전 검사 결과를 PPTX 리포트로 자동 생성하는 데스크톱 툴.",
  "tags": ["Python", "PPTX"],
  "status": "wip",               // wip | live | paused
  "last_commit": "2026-06-16",   // git, 없으면 null
  "links": { "repo": null, "live": null },  // 없으면 null → 링크 미표시
  "summary_stale": false          // scan.py가 표시, Claude가 채움
}
```

## 6. `scan.py` 동작 (자동 수집 항목)
- 두 소스 경로를 훑어 `exclude` 제외한 프로젝트 폴더 나열.
- 각 폴더에서: **도구**(소스 경로로 판별), **git last commit 날짜**(git 있으면), **기술 태그**(파일 확장자·마커: `.py`→Python, `pubspec`/`.kt`→Android, `_config.yml`→Jekyll, `index.html`→Web 등), **status 추정**(최근 커밋/Pages 여부), **링크**(git remote URL, 라이브 URL).
- **링크 규칙(섹션 4 결정):** git remote 있으면 `repo`, Pages 배포면 `live`. **로컬 전용(원격 없음)은 링크 없이 정보만** 표시(폴더 경로는 외부 노출 안 함).
- `summary`가 비었거나 폴더가 마지막 스캔 이후 변경됐으면 `summary_stale: true`로 표시 → Claude가 그 항목만 읽고 요약 채움(증분).

## 7. 요약 생성 (Claude 지능형, 증분)
1. `scan.py` 실행 → 자동 메타 갱신 + `summary_stale` 표시.
2. Claude가 `summary_stale` 항목만 해당 폴더(README/CLAUDE.md/코드)를 읽고 한줄 요약 작성·갱신.
3. 공개 URL이므로 요약엔 민감정보 없이, 가족 프로젝트는 톤 순화.

## 8. 갱신 워크플로우
`scan.py` 실행 → Claude가 빈 요약 채움 → `git push` → GitHub Pages 자동 반영.

## 9. 디자인 (확정)
- 컨셉 **"빌드 로그 / 청사진 콘솔"** — 다크 기본, IBM Plex Mono + IBM Plex Sans KR, 청사진 그리드 배경, 모노스페이스 로그 타일 카드, 앰버(`#E8A33D`) 강조(상태/활성에만), 대괄호 필터 칩, 6px 각진 모서리 + 1px 경계.
- 라이트/다크 토글, 카드 그리드 + 필터 칩(전체/도구/상태), 컴팩트 헤더(모바일 배려).
- 확정 산출물: `_workspace/02_design/index.html` (디자이너 하네스 산출). 이 파일을 `index.html` 템플릿으로 삼아 인라인 샘플 데이터를 `projects.json` fetch 렌더로 교체.

## 10. 배포 & 프라이버시
- GitHub에 `portfolio` repo 생성 → Pages 활성화(설정은 GitHub 웹에서 사용자가, 단계는 안내).
- 공개 URL 인지하에 진행. 민감 프로젝트는 `config.exclude`로 빼거나 요약 순화.

## 11. 범위에서 제외 (YAGNI)
- 실시간 서버/로그인/검색/태그 클라우드 등 부가기능 없음.
- 프로젝트 상세 페이지 없음(카드 + 외부 링크로 충분).
- 자동 cron/CI 갱신 없음(수동 `scan.py` + push).

## 12. 미해결/추후
- 로컬 전용 프로젝트를 나중에 GitHub에 올려 링크 추가할지(현재는 링크 없이).
- status 자동 추정 규칙의 세부 임계값(며칠 이상 무커밋이면 paused 등)은 구현 시 확정.
