# Auto_project - 全自动图文内容生产流水线

基于 AI 的全自动图文内容生产系统，实现从热点追踪、文案生成、AI 生图到多平台一键发布的完整流水线。

## 系统架构

`
Vue 3 前端 (:5173)
      |
      | REST API
      v
FastAPI 后端 (:8000)  <-- app/main.py 入口
      |
      +-- app/api/endpoints.py    (路由)
      +-- app/scrapers/           (热点采集)
      +-- app/generators/         (文案 + 生图)
      +-- app/publishers/         (多平台发布)
      +-- app/storage/            (数据库)
      +-- app/config.py           (配置加载)
      |
      +-- Docker: DailyHotApi (:6688)   (60+ 平台热搜)
      +-- Local:  ComfyUI (:8188)       (Stable Diffusion 生图)
      +-- Local:  MiMo API              (中文 LLM 文案)
      +-- Docker: PostgreSQL (:5434)    (数据存储)
`

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 前端 | Vue 3 + Vite + vue-router | SPA 管理界面 |
| 后端 | FastAPI (app 包架构) | REST API 服务 |
| 数据库 | PostgreSQL 16 (Docker) | 数据存储 |
| 热搜 | DailyHotApi (Docker) | 60+ 平台热搜聚合 |
| 文案 | MiMo API (mimo-v2.5-pro) | 中文 LLM |
| 生图 | ComfyUI 本地 | Stable Diffusion |
| 编排 | Python 3.9+ | CLI + API 双模式 |

## 目录结构

`
Auto_project/
  auto_pipeline.py              # CLI 主编排器（调用 app 内模块）
  app/                          # FastAPI 应用（所有后端逻辑都在这）
    main.py                     # 入口: 创建 FastAPI 实例、挂载路由
    config.py                   # 配置加载（TOML + .env）
    schemas.py                  # Pydantic 数据模型
    dependencies.py             # 依赖注入（Config）
    database.py                 # 数据库连接工厂
    api/
      __init__.py
      endpoints.py              # 所有 REST 接口（路由层）
    scrapers/
      __init__.py
      dailyhot.py               # DailyHotApi 热点采集
    generators/
      __init__.py
      script_gen.py             # MiMo API 文案生成（5 种 persona）
      image_gen.py              # ComfyUI 生图（多版本 workflow）
    publishers/
      __init__.py
      publisher.py              # 多平台发布 + Cookie 管理
    storage/
      __init__.py
      db.py                     # PostgreSQL CRUD（4 张表）
  docker-compose.yml            # PostgreSQL:5434 + DailyHotApi:6688
  pipeline_config.toml          # 配置文件
  requirements.txt              # Python 依赖
  .env / .env.example           # 环境变量
  frontend/                     # Vue 3 前端
    src/
      App.vue                   # 布局壳（侧边栏 + 内容区）
      router/index.js           # 路由（5 个页面）
      api/index.js              # API 服务层
      views/
        Dashboard.vue           # 仪表盘（状态总览 + 快速操作）
        Topics.vue              # 热点采集（采集 + 列表 + 生成文案入口）
        Scripts.vue             # 文案管理（生成 + 分镜预览 + 历史）
        Images.vue              # 图片管理（生成 + 多版本网格 + 审核选用）
        Publish.vue             # 发布管理（Cookie 状态 + 发布表单 + 结果）
      style.css                 # 全局样式
    vite.config.js              # Vite 配置（API 代理 -> :8000）
  docs/                         # 技术文档（5 篇）
  skills/auto-pipeline/         # Codex Skill
  pipeline_output/              # 生成内容输出
  photo_review/                 # 审核目录
  cookies/                      # 平台 Cookie
`

## 快速开始

### 1. 启动 Docker 服务

`powershell
docker compose up -d
docker ps   # 确认 postgres:5434 和 dailyhot-api:6688 运行
`

### 2. 安装 ComfyUI（如未安装）

`powershell
python skills/auto-pipeline/scripts/install_comfyui.py
cd ~/ComfyUI && python main.py --listen 127.0.0.1 --port 8188
`

### 3. 安装 Python 依赖

`powershell
pip install -r requirements.txt
pip install fastapi uvicorn
`

### 4. 配置环境变量

`powershell
Copy-Item .env.example .env
# 编辑 .env，填入 MIMO_API_KEY
`

### 5. 启动后端 API

`powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
`

### 6. 启动前端

`powershell
cd frontend
npm install
npm run dev
# 浏览器打开 http://localhost:5173
`

### 7. 或者用 CLI 模式

`powershell
python auto_pipeline.py --topic "AI技术发展" --review
`

## 运行模式

| 模式 | 入口 | 说明 |
|------|------|------|
| Web UI | 
pm run dev + uvicorn | 浏览器可视化管理 |
| CLI | python auto_pipeline.py | 命令行全自动/半自动 |

## API 接口

所有接口挂在 /api 前缀下:

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/status | 流水线状态 |
| GET | /api/config | 当前配置 |
| POST | /api/scrape | 采集热点 |
| POST | /api/script | 生成文案 |
| GET | /api/scripts | 列出脚本 |
| GET | /api/scripts/{name} | 获取脚本 |
| POST | /api/images | 生成图片 |
| GET | /api/images | 列出图片 |
| POST | /api/review/select | 图片审核选用 |
| POST | /api/publish | 发布内容 |
| GET | /api/cookies | Cookie 状态 |

## 配置说明

所有配置在 pipeline_config.toml，密钥在 .env。

## 故障排除

详见 docs/troubleshooting.md。