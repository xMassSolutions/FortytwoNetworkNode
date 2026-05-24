# Manual one-shot update for the FortytwoBot workstation agent.
#
# Run this from an admin PowerShell when you want to pull the latest
# code from origin/main and bounce the agent right now (instead of
# waiting up to 30 min for the built-in auto-updater).
#
# Handles:
#   - git pull --ff-only
#   - Cleanly ending the scheduled task
#   - Killing any stray powershell processes still running push-agent.ps1
#     (defensive -- a normal end usually cleans these up, but if a previous
#      restart didn't take, this guarantees the new code is what runs)
#   - Starting the scheduled task fresh
#   - Tailing the agent log so you can confirm the bootstrap push happened
#
# Usage (from any dir):
#   .\agent\update-agent.ps1
#
# Optional params:
#   -TaskName <name>   Scheduled-task name (default: FortytwoBotAgent)
#   -RepoRoot <path>   Repo root (default: parent of this script's dir)
#   -LogTail <n>       How many log lines to print at the end (default: 5)

param(
    [string]$TaskName = "FortytwoBotAgent",
    [string]$RepoRoot = (Split-Path $PSScriptRoot -Parent),
    [int]$LogTail = 5
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "=== Updating $TaskName ==="
Write-Host "Repo:   $RepoRoot"
Write-Host "Script: $PSScriptRoot"

Write-Host ""
Write-Host "[1/4] git pull --ff-only"
Set-Location -LiteralPath $RepoRoot
& git pull --ff-only
if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARN: git pull exited $LASTEXITCODE -- continuing anyway, but the restart may run old code." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/4] Stopping scheduled task + any stray push-agent processes"
& schtasks /End /TN $TaskName 2>&1 | ForEach-Object { Write-Host "  $_" }

try {
    $myPid = $PID
    $strays = Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" -ErrorAction SilentlyContinue |
              Where-Object {
                  $_.ProcessId -ne $myPid -and
                  ($_.CommandLine -like '*push-agent.ps1*' -or $_.CommandLine -like '*_agent-wrapper*')
              }
    foreach ($p in $strays) {
        Write-Host "  killing stray PID $($p.ProcessId)"
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    if (-not $strays) { Write-Host "  no stray processes" }
} catch {
    Write-Host "  (couldn't enumerate processes: $($_.Exception.Message))"
}

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "[3/4] Starting scheduled task"
& schtasks /Run /TN $TaskName 2>&1 | ForEach-Object { Write-Host "  $_" }

Start-Sleep -Seconds 10

Write-Host ""
Write-Host "[4/4] agent.log tail (last $LogTail lines):"
$logPath = Join-Path -Path $PSScriptRoot -ChildPath "agent.log"
if (Test-Path -LiteralPath $logPath) {
    Get-Content -LiteralPath $logPath -Tail $LogTail | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "  (agent.log not found at $logPath -- the agent may not have written yet)"
}

Write-Host ""
Write-Host "Done. Verify the dashboard meta line shows the latest agent_version SHA."
