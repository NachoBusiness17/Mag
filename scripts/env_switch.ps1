# Switch between cutting-edge Mag environment tracks (branch + port isolation).
# Usage:
#   .\scripts\env_switch.ps1 list
#   .\scripts\env_switch.ps1 use research
#   .\scripts\env_switch.ps1 status
#   .\scripts\env_switch.ps1 run research
#   .\scripts\env_switch.ps1 sync research
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet('list', 'use', 'status', 'run', 'sync')]
    [string]$Action,

    [Parameter(Position = 1)]
    [string]$TrackName
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot

function Get-Python {
    param([string]$RepoRoot)
    $venvPy = Join-Path $RepoRoot '.venv\Scripts\python.exe'
    if (Test-Path $venvPy) { return $venvPy }
    if (Get-Command py -ErrorAction SilentlyContinue) { return 'py' }
    return 'python'
}

function Invoke-EnvPython {
    param([string[]]$PyArgs)
    $Py = Get-Python $Root
    Push-Location $Root
    try {
        if ($Py -eq 'py') {
            & py -3 @PyArgs
        } else {
            & $Py @PyArgs
        }
        if ($null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) {
            throw "python exited $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
}

function Get-TrackJson {
    param([string]$Name)
    $Py = Get-Python $Root
    Push-Location $Root
    try {
        $code = @"
import json, sys
from mag.env_registry import get_track
t = get_track(sys.argv[1])
print(json.dumps(t) if t else 'null')
"@
        if ($Py -eq 'py') {
            $out = & py -3 -c $code $Name
        } else {
            $out = & $Py -c $code $Name
        }
    } finally {
        Pop-Location
    }
    if ($out -eq 'null' -or -not $out) {
        throw "Unknown track: $Name"
    }
    return $out | ConvertFrom-Json
}

function Sync-Track {
    param([string]$Name)
    Write-Host "== sync track: $Name =="
    $Py = Get-Python $Root
    Push-Location $Root
    try {
        $code = @"
import json, sys
from mag.env_registry import sync_track
print(json.dumps(sync_track(sys.argv[1])))
"@
        if ($Py -eq 'py') {
            $res = & py -3 -c $code $Name
        } else {
            $res = & $Py -c $code $Name
        }
        $obj = $res | ConvertFrom-Json
        if (-not $obj.ok) {
            Write-Error ($obj.error | Out-String)
        }
        Write-Host "Synced: $($obj.track) @ $($obj.root) [$($obj.branch)] port $($obj.port)"
        return $obj
    } finally {
        Pop-Location
    }
}

function Invoke-ActivateTrack {
    param([string]$Name)
    $Py = Get-Python $Root
    Push-Location $Root
    try {
        $code = @"
import json, sys
from mag.env_registry import activate_track
print(json.dumps(activate_track(sys.argv[1])))
"@
        if ($Py -eq 'py') {
            $res = & py -3 -c $code $Name
        } else {
            $res = & $Py -c $code $Name
        }
        $obj = $res | ConvertFrom-Json
        if (-not $obj.ok) {
            Write-Error ($obj.error | Out-String)
        }
        return $obj
    } finally {
        Pop-Location
    }
}

function Use-Track {
    param([string]$Name)
    Write-Host "== use track: $Name =="
    $obj = Invoke-ActivateTrack $Name
    Write-Host "Active environment: $Name @ $($obj.root) (.mag_active_env)"
    return $obj
}

function Start-TrackLab {
    param($Track, [string]$RepoRoot)
    $port = [int]$Track.port
    $Py = Get-Python $RepoRoot
    $mainPy = Join-Path $RepoRoot 'main.py'
    if (-not (Test-Path $mainPy)) {
        throw "main.py not found under $RepoRoot"
    }
    Write-Host "== lab on port $port ($RepoRoot) =="
    if ($Py -eq 'py') {
        Start-Process -WindowStyle Minimized -FilePath 'py' -ArgumentList @('-3', $mainPy, 'lab', '--port', "$port") -WorkingDirectory $RepoRoot
    } else {
        Start-Process -WindowStyle Minimized -FilePath $Py -ArgumentList @($mainPy, 'lab', '--port', "$port") -WorkingDirectory $RepoRoot
    }
    $deadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:$port/api/v1/health" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { break }
        } catch {}
    } while ((Get-Date) -lt $deadline)
    Write-Host "Dashboard: http://127.0.0.1:$port/"
}

switch ($Action) {
    'list' {
        Invoke-EnvPython @('-m', 'mag.env_registry', 'list')
    }
    'status' {
        Invoke-EnvPython @('-m', 'mag.env_registry', 'status')
    }
    'sync' {
        if (-not $TrackName) { throw 'sync requires a track name' }
        Sync-Track $TrackName | Out-Null
    }
    'use' {
        if (-not $TrackName) { throw 'use requires a track name' }
        Use-Track $TrackName
    }
    'run' {
        if (-not $TrackName) { throw 'run requires a track name' }
        $obj = Use-Track $TrackName
        Start-TrackLab -Track (Get-TrackJson $TrackName) -RepoRoot $obj.root
    }
}
