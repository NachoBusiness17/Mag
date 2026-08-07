# Pull narrative / IF / scifi inspiration corpus (OSS + PD). Catalog-only stays links.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\pull_narrative_corpus.ps1
# Optional: -AllRepos to also try large repos (openmw, inform)

param(
    [switch]$All,
    [switch]$SkipGit,
    [switch]$SkipPg
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not (Test-Path (Join-Path $Root "configs\narrative_corpus.yaml"))) {
    $Root = Join-Path $env:USERPROFILE "Documents\projects\local_sovereign_agent"
}
$Dest = Join-Path $Root "mine\raw\narrative_corpus"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Dest "public_domain") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root "memory\narrative_corpus") | Out-Null

Write-Host "ROOT $Root"
Write-Host "DEST $Dest"

$first = @(
    @{ id = "ink-language"; url = "https://github.com/inkle/ink.git" },
    @{ id = "ink-library"; url = "https://github.com/inkle/ink-library.git" },
    @{ id = "twinejs"; url = "https://github.com/klembot/twinejs.git" },
    @{ id = "redblob-roguelike"; url = "https://github.com/redblobgames/2126-roguelikedev.git" },
    @{ id = "tes5edit"; url = "https://github.com/TES5Edit/TES5Edit.git" }
)
$extra = @(
    @{ id = "inform"; url = "https://github.com/ganelson/inform.git" },
    @{ id = "quest"; url = "https://github.com/textadventures/quest.git" }
)

$repos = $first
if ($All) { $repos = $first + $extra }

if (-not $SkipGit) {
    foreach ($r in $repos) {
        $path = Join-Path $Dest $r.id
        Write-Host "`n=== $($r.id) ==="
        if (Test-Path (Join-Path $path ".git")) {
            Push-Location $path
            git pull --ff-only 2>&1 | Select-Object -Last 5
            Pop-Location
        } else {
            git clone --depth 1 $r.url $path 2>&1 | Select-Object -Last 8
        }
    }
}

if (-not $SkipPg) {
    $pg = @(
        @{ dest = "public_domain\wells_war_of_the_worlds.txt"; url = "https://www.gutenberg.org/files/36/36-0.txt" },
        @{ dest = "public_domain\wells_time_machine.txt"; url = "https://www.gutenberg.org/files/35/35-0.txt" }
    )
    foreach ($f in $pg) {
        $out = Join-Path $Dest $f.dest
        $dir = Split-Path $out -Parent
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        if (Test-Path $out) {
            Write-Host "exists $out"
            continue
        }
        Write-Host "fetch $($f.url)"
        try {
            Invoke-WebRequest -Uri $f.url -OutFile $out -UseBasicParsing -TimeoutSec 60
            Write-Host "wrote $out"
        } catch {
            Write-Host "fail $($_.Exception.Message)"
        }
    }
}

# Index stamp
$stamp = Join-Path $Root "memory\narrative_corpus\PULL_STAMP.txt"
@"
pulled=$(Get-Date -Format o)
dest=$Dest
repos=$($repos.id -join ',')
"@ | Set-Content -Path $stamp -Encoding utf8
Write-Host "`nDone. Stamp: $stamp"
Get-ChildItem $Dest -Directory | Select-Object Name
