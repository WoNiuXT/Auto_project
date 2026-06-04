# 故障排查手册

## Docker 相关

### 1. Docker Desktop 未运行

**症状**：`docker ps` 报错 "Cannot connect to the Docker daemon"

**解决**：
```powershell
# 启动 Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
# 等待 30 秒后重试
docker ps
```

### 2. 容器启动失败

**症状**：`docker ps -a` 显示容器 Exited

**排查**：
```powershell
docker logs pipeline-postgres
docker logs dailyhot-api
```

**常见原因**：
- 端口被占用 → 修改 docker-compose.yml 端口映射
- 磁盘空间不足 → `docker system prune` 清理
- 内存不足 → 关闭其他 Docker 容器

### 3. PostgreSQL 连接失败

**症状**：`connection refused` 或 `could not connect to server`

**排查**：
```powershell
# 确认容器运行
docker ps | findstr postgres

# 测试连接
docker exec pipeline-postgres psql -U pipeline -d pipeline -c "SELECT 1;"

# 从宿主机测试
python -c "import psycopg2; conn = psycopg2.connect(host='127.0.0.1', port=5434, user='pipeline', password='pipeline123', dbname='pipeline'); print('OK')"
```

**注意**：Windows 下 PostgreSQL 连接必须用 `127.0.0.1` 而非 `localhost`（IPv6 问题）。

### 4. DailyHotApi 无响应

**症状**：`Invoke-RestMethod http://localhost:6688` 超时

**解决**：
```powershell
docker compose restart dailyhot-api
docker logs dailyhot-api  # 查看错误信息
```

## ComfyUI 相关

### 5. ComfyUI 未安装

**症状**：`check_comfyui.py` 报告未找到

**解决**：
```powershell
python scripts/install_comfyui.py
# 或手动：
git clone https://github.com/comfyanonymous/ComfyUI.git $HOME\ComfyUI
cd $HOME\ComfyUI; pip install -r requirements.txt
```

### 6. ComfyUI 启动后无模型

**症状**：生图时报 "No checkpoint found"

**解决**：
```powershell
# 下载模型放到 checkpoints 目录
# SDXL: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
# 放到：~/ComfyUI/models/checkpoints/

# 使用 HuggingFace 镜像（国内）
$env:HF_ENDPOINT = "https://hf-mirror.com"
```

### 7. ComfyUI 生图很慢

**症状**：单张图 > 2 分钟

**排查**：
```powershell
# 检查是否使用 GPU
Invoke-RestMethod http://localhost:8188/system_stats | ConvertTo-Json -Depth 3
# 查看 devices 部分是否有 CUDA
```

**优化**：
- 确认使用 GPU（安装 CUDA 版 PyTorch）
- 减少 steps（默认 30 → 20）
- 使用更小的模型（SD 1.5 比 SDXL 快）

### 8. ComfyUI API 调用报错

**症状**：`POST /api/prompt` 返回 400 或 500

**排查**：
```powershell
# 检查 workflow JSON 格式
# 确认 ComfyUI 版本与 workflow 兼容
# 查看 ComfyUI 终端日志
```

## MiMo API 相关

### 9. API Key 无效

**症状**：401 Unauthorized

**解决**：
```powershell
# 检查 .env 文件
Get-Content .env | findstr MIMO_API_KEY

# 测试 API
$headers = @{"Authorization" = "Bearer $env:MIMO_API_KEY"; "Content-Type" = "application/json"}
$body = @{model="mimo-v2.5-pro"; messages=@(@{role="user"; content="hello"})} | ConvertTo-Json
Invoke-RestMethod -Uri "https://token-plan-cn.xiaomimimo.com/v1/chat/completions" -Method POST -Headers $headers -Body $body
```

### 10. API 响应超时

**症状**：请求挂起 > 60 秒

**解决**：
- 检查代理设置（.env 中 HTTP_PROXY）
- 减少 max_tokens
- 分镜数量从 5 减到 3

### 11. 分镜脚本解析失败

**症状**：MiMo 返回的内容不是有效 JSON

**解决**：
- 检查 prompt 模板格式
- 降低 temperature（0.8 → 0.5）提高稳定性
- 在 prompt 中明确要求返回 JSON 格式

## 发布相关

### 12. Cookie 失效

**症状**：发布报错 "Cookie expired" 或 401/403

**解决**：
```powershell
python scripts/check_cookies.py --platform douyin
# 按提示重新登录，导出 Cookie
```

### 13. 发布被限流

**症状**：429 Too Many Requests

**解决**：
- 增加 `publish.interval_seconds`（默认 30 → 60）
- 减少单次发布平台数
- 等待一段时间后重试

### 14. 图片上传失败

**症状**：图片格式或大小不支持

**解决**：
- 检查图片格式（PNG/JPEG）
- 检查图片大小（各平台限制不同，通常 < 20MB）
- 用 Pillow 压缩/转换格式

## 编码相关（Windows 特有）

### 15. 中文路径编码问题

**症状**：文件操作报错 UnicodeDecodeError

**解决**：
```powershell
# Python 文件始终用 UTF-8 No BOM
[System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding $false))

# open() 必须指定 encoding
open("file.txt", "r", encoding="utf-8")
```

### 16. PowerShell 管道脚本块错误

**症状**：`Expressions are only allowed as the first element of a pipeline`

**解决**：
```powershell
# 错误：... | { ... }
# 正确：先赋值再处理
$result = command
$result | ForEach-Object { ... }
```

## 性能相关

### 17. 全流水线执行慢

**优化建议**：
- 热点采集：并行请求多个平台（asyncio）
- 文案生成：减少分镜数量（5 → 3）
- 生图：减少变体数（3 → 2），使用更小模型
- 发布：并行发布到多平台（注意频率限制）