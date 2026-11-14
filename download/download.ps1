# 새로 생성된 쇼츠 영상을 내 PC로 받기 (Windows)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Repo = "amsul73/koreanword-shorts"
$Dest = Join-Path $env:USERPROFILE "Videos\korean-shorts"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "GitHub CLI(gh)가 설치되어 있지 않습니다."
    Write-Host "명령 프롬프트에서 다음을 실행한 뒤 다시 시도하세요:  winget install GitHub.cli"
    exit 1
}
gh auth status *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "처음 한 번 GitHub 로그인이 필요합니다. 브라우저 안내를 따라주세요."
    gh auth login --hostname github.com --git-protocol https --web
}

New-Item -ItemType Directory -Force $Dest | Out-Null
$tags = gh release list --repo $Repo --limit 200 --json tagName --jq '.[].tagName' |
    Where-Object { $_ -match '^(vocab|basic|grammar|longform)_day' }

$new = 0
foreach ($t in $tags) {
    $dir = Join-Path $Dest $t
    if (Test-Path (Join-Path $dir "*.mp4")) { continue }
    gh release download $t --repo $Repo --dir $dir --clobber
    if ($LASTEXITCODE -eq 0) { Write-Host "받음: $t"; $new++ }
}
Write-Host ""
Write-Host "새 영상 $new 개  /  저장 폴더: $Dest"
if ($new -gt 0) { Invoke-Item $Dest }
