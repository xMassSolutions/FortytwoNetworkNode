param(
    [Parameter(Mandatory)] [string]$BotUrl,
    [Parameter(Mandatory)] [string]$AgentToken,
    # OPTIONAL: omit for auto-discovery -- ONE agent reports every FortyTwo node
    # on this PC (recommended). Pass a path to pin the agent to a single node
    # (legacy mode; also required for a -DockerContainer node).
    [string]$ScriptsRoot = "",
    [string]$DockerContainer = "",
    # Legacy single-node knobs (ignored in auto mode -- ids are auto-assigned).
    [int]$NodeId = 1,
    [string]$NodeWallet = "",
    # Task name. Defaults to "FortytwoBotAgent" in auto mode, or
    # "FortytwoBotAgent-Node<N>" for a pinned single-node install.
    [string]$TaskName = ""
)

# No -ScriptsRoot => auto-discovery (one agent per machine).
$AutoMode = -not $ScriptsRoot
if (-not $TaskName) {
    $TaskName = if ($AutoMode) { "FortytwoBotAgent" } else { "FortytwoBotAgent-Node$NodeId" }
}

$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $here "push-agent.ps1"
if (-not (Test-Path $script)) { throw "push-agent.ps1 not found at $script" }

# Wrapper that sets env vars, logs to a rolling file, and restarts the agent if it dies
$wrapper = Join-Path $here "_agent-wrapper.ps1"
$logFile = Join-Path $here "agent.log"

# In auto mode the wrapper passes no per-node flags -- the agent discovers every
# node and assigns stable ids itself. In legacy mode it pins to one ScriptsRoot.
if ($AutoMode) {
    $envLines = ""
    $invoke   = "& '$script' *>> '$logFile'"
} else {
    $dockerArg = if ($DockerContainer) { "-DockerContainer '$DockerContainer' " } else { "" }
    # Only emit FORTYTWO_NODE_WALLET when provided -- an empty value would fail
    # the server's hex-address validator on every push.
    $nodeWalletLine = if ($NodeWallet) { "`$env:FORTYTWO_NODE_WALLET = '$NodeWallet'`r`n" } else { "" }
    $envLines = "`$env:FORTYTWO_NODE_ID = '$NodeId'`r`n$nodeWalletLine"
    $invoke   = "& '$script' -ScriptsRoot '$ScriptsRoot' $dockerArg*>> '$logFile'"
}

$wrapperContent = @"
`$env:FORTYTWO_BOT_URL = '$BotUrl'
`$env:FORTYTWO_AGENT_TOKEN = '$AgentToken'
$envLines
while (`$true) {
    try {
        $invoke
    } catch {
        ('agent died: ' + `$_.Exception.Message + ' - restarting in 10s') | Out-File -FilePath '$logFile' -Append
        Start-Sleep -Seconds 10
    }
}
"@
Set-Content -Path $wrapper -Value $wrapperContent -Encoding UTF8

$action    = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$wrapper`""
$trigger   = New-ScheduledTaskTrigger -AtLogOn
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null

$modeDesc = if ($AutoMode) { "auto-discovery (every local node)" } else { "single node: $ScriptsRoot" }
Write-Output "Scheduled Task '$TaskName' installed -- mode: $modeDesc."
Write-Output "Wrapper: $wrapper"
Write-Output "Logs:    $logFile"
Write-Output ""
Write-Output "Starting now..."
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 2
Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo | Format-List TaskName, LastRunTime, LastTaskResult, NextRunTime
