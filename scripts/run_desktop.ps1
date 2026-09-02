# 桌面窗。Gateway 需已在跑。
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
& "$Root\.venv\Scripts\python.exe" -m clients.desktop @args
