# 必须带镜像环境变量，否则会去连 huggingface.co 超时
$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:HUGGINGFACE_HUB_ENDPOINT = "https://hf-mirror.com"
$env:HF_HUB_DISABLE_XET = "1"
Write-Host "HF_ENDPOINT=$env:HF_ENDPOINT"
Write-Host "模型服务: http://127.0.0.1:8000"
Write-Host "聊天界面: http://127.0.0.1:8080"
transformers serve
