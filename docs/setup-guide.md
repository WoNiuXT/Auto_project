# 安装部署指南

## 前置条件

- Windows 10/11
- PowerShell 5.1+
- Docker Desktop（已安装并运行）
- Python 3.9+
- Git
- 推荐：NVIDIA GPU + CUDA（ComfyUI 生图加速）

## 第一步：环境准备

### 1.1 确认 Docker 运行

```powershell
docker --version
docker ps
```

如果 Docker 未运行，启动 Docker Desktop。

### 1.2 确认 Python 版本

```powershell
python --version
# 应显示 3.9.x 或更高
```

### 1.3 配置代理（如需访问外网）

```powershell
# PowerShell 环境变量
$env:HTTP_PROXY = "http://127.0.0.1:7897"
$env:HTTPS_PROXY = "http://127.0.0.1:7897"

# Git 代理
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897
```

## 第二步：安装 ComfyUI

### 自动安装

```powershell
python scripts/install_comfyui.py
```

脚本会：
1. git clone ComfyUI 到 `~/ComfyUI`
2. pip install 依赖
3. 提示下载推荐模型

### 手动安装

```powershell
# 克隆
git clone https://github.com/comfyanonymous/ComfyUI.git $HOME\ComfyUI
cd $HOME\ComfyUI

# 安装依赖
pip install -r requirements.txt

# 下载模型（放到 models/checkpoints/）
# 推荐模型：
#   - SDXL 1.0: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
#   - DreamShaper XL: https://huggingface.co/Lykon/dreamshaper-xl-v2-turbo
# 下载后放到：~/ComfyUI/models/checkpoints/
```

### 启动 ComfyUI

```powershell
cd $HOME\ComfyUI
python main.py --listen 127.0.0.1 --port 8188
```

验证：
```powershell
Invoke-RestMethod http://localhost:8188/system_stats
```

## 第三步：启动 Docker 服务

```powershell
cd D:\Agent_Project\Auto_project

# 启动 PostgreSQL + DailyHotApi
docker compose up -d

# 确认运行状态
docker ps
# 应看到：
#   pipeline-postgres    :5434
#   dailyhot-api         :6688
```

验证服务：
```powershell
# 测试 DailyHotApi
Invoke-RestMethod http://localhost:6688/weibo | ConvertTo-Json -Depth 2

# 测试 PostgreSQL
docker exec pipeline-postgres psql -U pipeline -d pipeline -c "SELECT 1;"
```

## 第四步：安装 Python 依赖

```powershell
pip install -r requirements.txt
```

核心依赖：
- `httpx` — 异步 HTTP 客户端
- `toml` — 配置文件解析
- `rich` — 终端美化输出 + 审核交互
- `Pillow` — 图片处理
- `psycopg2-binary` — PostgreSQL 驱动
- `tenacity` — 重试机制

## 第五步：配置

### 5.1 复制环境变量模板

```powershell
Copy-Item .env.example .env
```

### 5.2 编辑 .env

```env
MIMO_API_KEY=your-mimo-api-key-here
HTTP_PROXY=http://127.0.0.1:7897
HTTPS_PROXY=http://127.0.0.1:7897
```

### 5.3 检查 pipeline_config.toml

默认配置已可直接使用。按需修改：
- `[dailyhot].platforms` — 采集哪些平台
- `[script].persona` — 文案人设
- `[image].variants` — 每场景生图数
- `[publish].platforms` — 发布平台

## 第六步：验证完整流水线

```powershell
# 只采集热点（测试 DailyHotApi）
python auto_pipeline.py --step scrape

# 只生成文案（测试 MiMo API）
python auto_pipeline.py --step script --topic "AI技术发展"

# 完整流水线（带审核）
python auto_pipeline.py --topic "AI技术发展" --review
```

## 常见安装问题

### ComfyUI 安装失败

```powershell
# 检查 Git
git --version

# 手动克隆（如果自动脚本失败）
git clone https://github.com/comfyanonymous/ComfyUI.git $HOME\ComfyUI
```

### Docker 容器启动失败

```powershell
# 查看日志
docker logs pipeline-postgres
docker logs dailyhot-api

# 重建容器
docker compose down
docker compose up -d --build
```

### MiMo API 调用失败

```powershell
# 测试 API Key
$headers = @{
    "Authorization" = "Bearer $env:MIMO_API_KEY"
    "Content-Type" = "application/json"
}
$body = @{
    model = "mimo-v2.5-pro"
    messages = @(@{role="user"; content="你好"})
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://token-plan-cn.xiaomimimo.com/v1/chat/completions" `
    -Method POST -Headers $headers -Body $body
```

### 端口被占用

```powershell
# 查看端口占用
netstat -ano | findstr ":5434"
netstat -ano | findstr ":6688"
netstat -ano | findstr ":8188"

# 修改 docker-compose.yml 中的端口映射
```