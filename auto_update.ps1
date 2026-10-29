# 매일 자동 갱신: 폴더를 스캔해 projects.json(메타데이터·진행 로그)을 새로 쓰고,
# 바뀐 게 있을 때만 커밋·푸시한다. 새 프로젝트 요약은 비어 있으니 나중에 Claude에게 채워 달라고 하면 된다.
# Windows 작업 스케줄러 "Portfolio-Daily-Update"가 매일 실행한다.

Set-Location $PSScriptRoot
$log = Join-Path $PSScriptRoot "_workspace\auto_update.log"
function Write-Log($msg) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg" | Out-File -FilePath $log -Append -Encoding utf8 }

Write-Log "start"
$scan = & python -X utf8 scan.py 2>&1
Write-Log ($scan -join " | ")
if ($LASTEXITCODE -ne 0) { Write-Log "scan failed (exit $LASTEXITCODE)"; exit 1 }

git diff --quiet -- projects.json
if ($LASTEXITCODE -eq 0) { Write-Log "no changes"; exit 0 }

git add projects.json
git commit -q -m "data: daily auto update"
git push -q origin main
if ($LASTEXITCODE -ne 0) { Write-Log "push failed (exit $LASTEXITCODE)"; exit 1 }
Write-Log "pushed"
