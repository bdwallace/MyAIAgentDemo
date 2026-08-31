# 用国内镜像下载 Qwen2.5-3B（约 6GB，适合本机试 V0）
$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:HUGGINGFACE_HUB_ENDPOINT = "https://hf-mirror.com"
$env:HF_HUB_DISABLE_XET = "1"
Write-Host "从 hf-mirror 下载 Qwen/Qwen2.5-3B-Instruct ..."
python -c "from huggingface_hub import snapshot_download; print(snapshot_download('Qwen/Qwen2.5-3B-Instruct'))"
