---
name: auto-pipeline
description: |
  Use when asked to: (1) build an automated image-text content pipeline, (2) set up
  热点追踪/AI文案生成/ComfyUI生图/多平台发布, (3) configure 自动化内容生产 or
  图文自动化 workflow, (4) integrate DailyHotApi/ComfyUI/MiMo API into a pipeline,
  (5) start an image-text automation project from scratch.
  Triggers: content pipeline, 自动发布, 热点采集, AI生图, ComfyUI pipeline,
  DailyHotApi, 多平台发布, 图文流水线, auto publish.
---

# 全自动图文内容生产流水线

## 核心架构

```
DailyHotApi (:6688) -> 热点聚合 -> MiMo API 文案 -> ComfyUI 生图(多版本) -> 多平台发布
```

唯一热点源：DailyHotApi（60+ 平台热搜，Docker 容器）。

## 环境依赖

- Python 3.9+，依赖见 `templates/requirements.txt`
- Docker Desktop（PostgreSQL + DailyHotApi）
- ComfyUI 本地安装（端口 8188）
- FastAPI + uvicorn（后端 API 服务，端口 8000）
- Vue 3 + Vite + vue-router（前端，端口 5173）
- MiMo API Key（.env 中 MIMO_API_KEY）

## 前置条件检查（每次运行先执行）

1. 运行 `scripts/check_comfyui.py` — 确认 ComfyUI 已安装、运行中（:8188）
   - 若未安装，运行 `scripts/install_comfyui.py` 自动安装
2. 运行 `scripts/check_dailyhot.py` — 确认 DailyHotApi 容器运行中（:6688）
3. 检查 `.env` 中 `MIMO_API_KEY` 存在且非空

任何一项失败 → 给出修复指引后停止，不继续。

## 项目初始化（仅首次）

从 `templates/` 复制以下文件到目标项目目录：
- `docker-compose.yml` → PostgreSQL:5434 + DailyHotApi:6688
- `pipeline_config.toml` → 配置模板（密钥用 env() 引用 .env）
- `.env.example` → 复制为 `.env`，提醒用户填入 MIMO_API_KEY
- `requirements.txt` → pip install -r requirements.txt

生成目录结构：

```
项目目录/
  auto_pipeline.py            # 主编排器
  pipeline_config.toml / .env / requirements.txt / docker-compose.yml
  pipeline/
    scrapers/dailyhot.py      # 热点采集
    generators/script_gen.py  # MiMo 文案
    generators/image_gen.py   # ComfyUI 生图
    publishers/publisher.py   # 多平台发布
    storage/db.py             # PostgreSQL
  pipeline_output/ / photo_library/ / photo_review/
```

## 阶段一：热点采集

数据源：DailyHotApi REST API（`http://127.0.0.1:6688/{platform}`）。
支持平台：weibo, zhihu, bilibili, douyin, baidu, toutiao 等。

流程：
1. 调用 DailyHotApi 获取多个平台热搜
2. 按热度排序，排除 `pipeline_config.toml` 中 `exclude_keywords` 匹配的条目
3. 若用户指定 `--topic "xxx"`，优先使用用户话题
4. 输出：话题列表（标题 + 热度 + 来源链接）

## 阶段二：AI 文案生成

引擎：MiMo API（`https://token-plan-cn.xiaomimimo.com/v1`，兼容 OpenAI 格式）。

流程：
1. 从 `references/prompt-templates.md` 选择匹配 persona 的 prompt 模板
2. 构建 prompt：话题 + persona + 分镜数 + 风格
3. 调用 MiMo API，解析返回的结构化分镜脚本 JSON
4. 保存到 `pipeline_output/{timestamp}_script.json`

分镜脚本字段：`topic`, `persona`, `scenes[].scene_id`, `scenes[].narration`, `scenes[].image_prompt`, `scenes[].style_keywords`。
JSON 示例见 `references/prompt-templates.md`。

## 阶段三：ComfyUI 生图（多版本）

引擎：ComfyUI 本地（:8188）。Workflow 模板见 `references/comfyui-workflows.md`。

多版本策略：每场景生成 N 张（默认 3，`image.variants` 配置），不同 seed。

流程：
1. 读取分镜脚本中的 `image_prompt` + `style_keywords`
2. 从 `references/comfyui-workflows.md` 加载 txt2img workflow 模板
3. 为每个场景生成 N 个变体（不同 seed）
4. 保存到 `pipeline_output/{timestamp}/`，生成 `manifest.json` 索引

## 阶段四：审核（--review 模式）

自动模式（默认）：使用每场景 v1，跳过审核。

审核模式（`--review` 或 `review.enabled = true`）：
1. 展示每个场景的多版本图片（rich 终端 + 文件路径）
2. 用户选择最佳版本（v1/v2/v3 或跳过）
3. 选中图片复制到 `photo_review/`，确认后继续发布

## 阶段五：多平台发布

前置检查：运行 `scripts/check_cookies.py` 验证 Cookie 有效性。
详细发布指南见 `references/platform-publish-guide.md`。

支持平台：douyin（抖音）、bilibili（B站）、xhs（小红书）。

Cookie 管理策略：
- 首次：引导用户手动登录导出 Cookie（cookies/ 目录）
- 运行前：`scripts/check_cookies.py` 验证
- 失效：提示重新登录，不自动重试（防账号风控）
- 频率：平台间间隔 >= 30 秒

发布流程：
1. Cookie 检查 → 失效则停止
2. 准备内容（图片 + 文案 + 话题标签）
3. 按 `publish.platforms` 顺序逐平台发布
4. 记录结果到 PostgreSQL
5. 失败平台记录错误，不阻塞其他平台

## 错误处理

| 场景 | 处理 |
|------|------|
| DailyHotApi 无响应 | docker compose restart，重试 2 次 |
| MiMo API 超时 | tenacity 重试 3 次（间隔 2/4/8s），失败则跳过该话题 |
| MiMo 返回非 JSON | 降低 temperature（0.8->0.5）重试一次 |
| ComfyUI OOM | 减小图片尺寸（1024->768）重试 |
| ComfyUI 无响应 | 提示检查服务，重试 2 次 |
| Cookie 失效 | 跳过该平台，记录错误 |
| 发布网络超时 | 重试 2 次（间隔 5s），仍失败则跳过 |
| 发布被限流(429) | 等待 60s 后重试 |
| 账号风控 | 立即停止该平台，不重试 |

## 命令行接口

```bash
python auto_pipeline.py --topic "AI技术发展"             # 全自动
python auto_pipeline.py --topic "AI技术发展" --review     # 带审核
python auto_pipeline.py --step scrape                     # 只采集
python auto_pipeline.py --step script --topic "话题"       # 只文案
python auto_pipeline.py --step images                     # 只生图
python auto_pipeline.py --step publish                    # 只发布
python auto_pipeline.py --topic "话题" --variants 5        # 更多版本
python auto_pipeline.py --topic "话题" --platforms douyin   # 指定平台
python auto_pipeline.py --topic "话题" --variants 5        # 更多版本
python auto_pipeline.py --topic "话题" --platforms douyin   # 指定平台
python auto_pipeline.py --help                            # 帮助
```

## 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 热点源 | DailyHotApi 唯一 | 60+ 平台已覆盖，不需要额外服务 |
| 文案 | MiMo API | 已有 key，中文质量好，OpenAI 兼容 |
| 生图 | ComfyUI 本地 | 质量最高，可控，无 API 费用 |
| 质量 | 多版本 + 审核 | 单次生成质量不稳定 |
| DB | PostgreSQL | 与现有项目一致，Docker 部署 |
| 密钥 | .env only | TOML 不存密钥 |