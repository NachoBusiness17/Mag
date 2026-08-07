# Mag PowerShell front door — forwards to mag.cmd (PowerShell requires .\ prefix)
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$cmd = Join-Path $root "mag.cmd"
& $cmd @Args
exit $LASTEXITCODE
