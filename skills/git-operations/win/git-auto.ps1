# Git Auto Helper for Windows
param(
    [string]$RootDir = ".",
    [ValidateSet("status","pull","commit-push")]
    [string]$Operation = "status",
    [string]$Message = "Auto commit"
)

$repos = Get-ChildItem -Path $RootDir -Directory | Where-Object { Test-Path (Join-Path $_.FullName ".git") }

foreach ($repo in $repos) {
    Write-Host "[$($repo.Name)] Operation: $Operation" -ForegroundColor Cyan
    Push-Location $repo.FullName
    try {
        switch ($Operation) {
            "status" { git status --short }
            "pull"   { git pull }
            "commit-push" {
                git add .
                git commit -m "$Message"
                git push
            }
        }
    }
    finally {
        Pop-Location
    }
}
