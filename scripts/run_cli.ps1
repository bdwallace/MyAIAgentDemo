# 终端客户端，和网页共用 Gateway
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
& "$Root\.venv\Scripts\python.exe" -m clients.cli @args
