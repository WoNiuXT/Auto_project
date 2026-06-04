# 架构设计详解

## 设计目标

构建一个半自动化的图文内容生产流水线，平衡自动化效率和内容质量。

## 核心设计决策

### 1. 唯一热点源：DailyHotApi

**选择理由**：
- DailyHotApi 已整合 60+ 平台热搜（微博/知乎/B站/抖音/百度/头条/快手/小红书等）
- 通过 Docker 容器运行，零配置即可使用
- RESTful API，返回结构化 JSON
- 活跃维护（imsyy/DailyHotApi，10k+ stars）

**为什么不选 TrendRadar**：
- DailyHotApi 已覆盖相同平台，功能重叠
- TrendRadar 额外增加一个容器的维护成本
- 保持架构简单：单一数据源，单一接口

### 2. 文案引擎：MiMo API

**选择理由**：
- 用户已验证 API 可用性
- 中文生成质量好（小米模型，中文优化）
- 兼容 OpenAI API 格式，切换成本低
- 成本可控

**API 格式**：
```
POST https://token-plan-cn.xiaomimimo.com/v1/chat/completions
Authorization: Bearer {api_key}
```

### 3. 生图引擎：ComfyUI 本地

**选择理由**：
- 本地运行，无 API 费用
- 模型可自由切换（SD 1.5 / SDXL / Flux 等）
- Workflow 可定制，质量可控
- 支持 LoRA/ControlNet 等扩展

**调用方式**：
```
POST http://127.0.0.1:8188/api/prompt
Body: ComfyUI workflow JSON
```

**为什么不选 Pollinations.ai**：
- 质量不如本地 ComfyUI + 专业模型
- 依赖外部服务，有速率限制
- 无法使用 LoRA 微调风格

### 4. 质量策略：多版本 + 审核

**问题**：AI 一次生成的内容质量不稳定，参考 MoneyPrinterTurbo 的教训。

**方案**：
- 每个分镜生成 N 个变体（默认 3 个，不同 seed）
- `--review` 模式：人工挑选最佳版本
- 自动模式：使用 v1（第一个版本）
- 未来可加入 AI 自动评分选最佳

### 5. 数据库：PostgreSQL

**用途**：
- 存储热点话题（去重、历史追溯）
- 存储分镜脚本（版本管理）
- 记录图片生成结果
- 记录发布状态

**为什么不用 SQLite**：
- 与用户现有项目（Agent_project02 的 pgvector）保持一致
- Docker 部署方便，不需要本地安装
- 未来可扩展为多用户/多项目

## 数据流

```
用户输入话题（可选）
      |
      v
DailyHotApi 采集热搜
      |
      v
话题筛选（去重 + 排除关键词）
      |
      v
MiMo API 生成分镜脚本
      |  输出：script.json（5 个场景，每个含 image_prompt）
      v
ComfyUI 生图（每个场景 3 个变体）
      |  输出：pipeline_output/{timestamp}/scene1_v1.png, v2.png, v3.png ...
      v
审核（--review 模式）或自动选择
      |
      v
多平台发布（抖音/B站/小红书）
      |
      v
记录到 PostgreSQL
```

## 模块职责

### pipeline/scrapers/dailyhot.py
- 调用 DailyHotApi REST API
- 支持多平台并行采集
- 按热度排序、关键词过滤
- 去重（与数据库中已有话题比对）

### pipeline/generators/script_gen.py
- 管理 prompt 模板（按 persona 分类）
- 构建 MiMo API 请求
- 解析返回的结构化分镜脚本
- 锅误处理 + 重试（tenacity）

### pipeline/generators/image_gen.py
- 构建 ComfyUI workflow JSON
- 管理 prompt 变体生成（不同 seed）
- 异步调用 ComfyUI API
- 监听生成进度
- 保存图片 + 生成 manifest

### pipeline/publishers/publisher.py
- Cookie 状态管理
- 按平台适配器模式发布
- 频率限制（platform 间隔 >= 30s）
- 发布结果记录

### pipeline/storage/db.py
- 连接池管理（asyncpg 或 psycopg2）
- CRUD 操作封装
- 数据库初始化（建表）

## 安全设计

- API Key 只存在 `.env`，`pipeline_config.toml` 不存密钥
- Cookie 文件不入版本控制（.gitignore）
- 发布失败不自动重试（避免账号风险）
- 频率限制防止被平台封号

## 扩展性

- **新增平台**：在 publishers/ 添加平台适配器，配置中添加平台名
- **切换 LLM**：修改 script_gen.py 的 API endpoint（兼容 OpenAI 格式）
- **切换生图**：修改 image_gen.py（支持 ComfyUI / SD WebUI / 其他）
- **新增热点源**：在 scrapers/ 添加采集器（如需要）