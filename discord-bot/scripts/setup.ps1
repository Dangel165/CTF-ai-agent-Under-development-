# Run inside WSL: bash scripts/setup.sh
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Write-Host "Launching setup in WSL..."
wsl bash -lc "cd '$(wsl wslpath -a $Root)' && bash scripts/setup.sh"
