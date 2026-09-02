# Celery worker 必须在本机跑：要共用 .venv 和 modelscope 向量缓存。
# Windows 不要用默认 prefork，用 --pool=solo。
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$celery = Join-Path $Root ".venv\Scripts\celery.exe"
if (-not (Test-Path $celery)) {
    Write-Error "找不到 .venv\Scripts\celery.exe。先执行: .venv\Scripts\Activate.ps1; pip install -r requirements.txt"
    exit 1
}
Write-Host "Celery worker  (broker 默认 redis://127.0.0.1:6379/0)"
Write-Host "项目根目录: $Root"
$env:PYTHONPATH = $Root
& $celery -A worker.celery_app worker -l info --pool=solo --concurrency=1
