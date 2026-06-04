# Auto_pipeline - 全自动图文内容生产流水线

热点采集 → AI 文案生成 → ComfyUI 生图(多版本) → 人工审核 → 多平台发布

## 技术栈

### 后端 (`app/`)

| 模块 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI + Uvicorn | RESTful API 服务 |
| 数据库 | PostgreSQL 16 + psycopg2 | 持久化存储话题/文案/图片/发布记录 |
| AI 文案 | MiMo API (mimo-v2.5-pro) | 小米大模型，生成分镜脚本 |
| 图片生成 | ComfyUI (SDXL) | 本地 Stable Diffusion 推理引擎 |
| 热点采集 | DailyHot API | 多平台热搜聚合（微博/知乎/B站/抖音） |
| 多平台发布 | Playwright | 浏览器自动化发布（抖音/B站/小红书） |
| 配置管理 | TOML + .env | 业务配置 TOML，密钥 .env |
| HTTP 客户端 | httpx | 异步 HTTP 请求 |

### 前端 (`frontend/`)

| 模块 | 技术 | 说明 |
|------|------|------|
| 框架 | Vue 3 | Composition API |
| 路由 | Vue Router 4 | SPA 路由 |
| 构建 | Vite 8 | 开发服务器 + 构建工具 |

### 基础设施

| 服务 | 端口 | 说明 |
|------|------|------|
| FastAPI 后端 | 8000 | API 服务 |
| Vue 前端 | 5173 | 管理界面 |
| ComfyUI | 8188 | 图片生成引擎 |
| DailyHot API | 6688 | 热搜数据源 |
| PostgreSQL | 5434 | 数据库 |

## 目录结构

```
Auto_project/
├── app/                        # 后端 FastAPI 应用
│   ├── api/
│   │   └── endpoints.py        # API 路由
│   ├── generators/
│   │   ├── image_gen.py        # ComfyUI 生图
│   │   ├── script_gen.py       # MiMo 文案生成
│   │   └── tts_gen.py          # TTS 语音合成
│   ├── publishers/
│   │   └── publisher.py        # 多平台发布
│   ├── scrapers/
│   │   └── dailyhot.py         # 热搜采集
│   ├── storage/
│   │   └── db.py               # 数据库操作
│   ├── config.py               # 配置加载
│   ├── database.py             # DB 依赖注入
│   ├── dependencies.py         # 通用依赖
│   ├── main.py                 # FastAPI 入口
│   └── schemas.py              # Pydantic 数据模型
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── api/                # API 调用封装
│   │   ├── components/         # 通用组件
│   │   ├── router/             # 路由配置
│   │   ├── stores/             # 状态管理
│   │   └── views/              # 页面视图
│   │       ├── Dashboard.vue   # 仪表盘
│   │       ├── Topics.vue      # 话题管理
│   │       ├── Scripts.vue     # 文案管理
│   │       ├── Images.vue      # 图片管理
│   │       └── Publish.vue     # 发布管理
│   └── package.json
├── skills/                     # Codex 技能配置
├── auto_pipeline.py            # CLI 入口（命令行流水线）
├── pipeline_config.toml        # 业务配置
├── docker-compose.yml          # Docker 服务编排
├── requirements.txt            # Python 依赖
├── start.bat                   # 一键启动
├── stop.bat                    # 一键停止
├── .env                        # 环境变量（密钥，不提交）
└── .gitignore
```

## 快速开始

### 1. 环境准备

```powershell
# Python 依赖
pip install -r requirements.txt

# 前端依赖
cd frontend && npm install
```

### 2. 配置

```powershell
# 复制并编辑环境变量
cp .env.example .env
# 编辑 .env 填入 MIMO_API_KEY
```

### 3. 启动

```powershell
# 一键启动所有服务
.\start.bat

# 或手动启动：
docker compose up -d                          # PostgreSQL + DailyHot
python -m uvicorn app.main:app --port 8000    # 后端
cd frontend && npm run dev                    # 前端
```

### 4. 使用

- **Web 界面**: http://127.0.0.1:5173
- **API 文档**: http://127.0.0.1:8000/docs
- **CLI 模式**: `python auto_pipeline.py --topic "AI技术发展"`

## CLI 用法

```powershell
# 全自动流水线
python auto_pipeline.py --topic "AI技术发展"

# 带人工审核
python auto_pipeline.py --topic "AI技术发展" --review

# 单步执行
python auto_pipeline.py --step scrape              # 只采集
python auto_pipeline.py --step script --topic "XX"  # 只文案
python auto_pipeline.py --step images               # 只生图
python auto_pipeline.py --step publish              # 只发布
```