param(
    # By default remove the auto-discovery task AND any legacy per-node tasks
    # (FortytwoBotAgent-Node<N>). Pass a specific -TaskName to target just one.
    [string]$TaskName = ""
)

if ($TaskName) {
    $targets = @(Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)
} else {
    $targets = @(Get-ScheduledTask -ErrorAction SilentlyContinue |
        Where-Object { $_.TaskName -eq "FortytwoBotAgent" -or $_.TaskName -like "FortytwoBotAgent-Node*" })
}

if (-not $targets -or $targets.Count -eq 0) {
    Write-Output "No FortytwoBotAgent task(s) found."
    return
}

foreach ($t in $targets) {
    Stop-ScheduledTask -TaskName $t.TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $t.TaskName -Confirm:$false
    Write-Output "Task '$($t.TaskName)' removed."
}
