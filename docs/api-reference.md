# API 接口参考

## DailyHotApi（热搜聚合）

基础 URL：`http://localhost:6688`

### GET /{platform}

获取指定平台热搜列表。

**支持的平台**：

| 平台 | 路径 | 说明 |
|------|------|------|
| 微博 | /weibo | 微博热搜 |
| 知乎 | /zhihu | 知乎热榜 |
| B站 | /bilibili | B站热门 |
| 抖音 | /douyin | 抖音热搜 |
| 百度 | /baidu | 百度热搜 |
| 头条 | /toutiao | 今日头条 |
| 快手 | /kuaishou | 快手热搜 |
| 小红书 | /xiaohongshu | 小红书热门 |

**响应格式**：
```json
[
  {
    "title": "话题标题",
    "hot": 1234567,
    "url": "https://...",
    "description": "话题描述"
  }
]
```

### GET /

返回 DailyHotApi 服务信息和支持的平台列表。

## MiMo API（文案生成）

基础 URL：`https://token-plan-cn.xiaomimimo.com/v1`

兼容 OpenAI Chat Completions API 格式。

### POST /chat/completions

**请求头**：
```
Authorization: Bearer {MIMO_API_KEY}
Content-Type: application/json
```

**请求体**：
```json
{
  "model": "mimo-v2.5-pro",
  "messages": [
    {"role": "system", "content": "你是一个知识科普博主..."},
    {"role": "user", "content": "请为以下话题生成5个分镜脚本..."}
  ],
  "temperature": 0.8,
  "max_tokens": 2000
}
```

**响应**：OpenAI 标准格式，`choices[0].message.content` 为分镜脚本 JSON。

## ComfyUI API（本地生图）

基础 URL：`http://localhost:8188`

### GET /system_stats

检查 ComfyUI 服务状态。

### POST /api/prompt

提交生图任务。

**请求体**：ComfyUI workflow JSON（节点图）。

**关键节点**：
- `KSampler` — 采样器（seed/steps/cfg/sampler_name）
- `CLIPTextEncode` — 正向/负向 prompt
- `CheckpointLoaderSimple` — 加载模型
- `SaveImage` — 保存图片

**响应**：
```json
{
  "prompt_id": "uuid-string",
  "number": 1,
  "node_errors": {}
}
```

### GET /history/{prompt_id}

查询生图任务状态和结果。

## PostgreSQL（数据存储）

连接信息：
- 地址：`127.0.0.1:5434`
- 用户：`pipeline`
- 密码：`pipeline123`
- 数据库：`pipeline`

### 核心表结构

#### topics（热点话题）
```sql
CREATE TABLE topics (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    source VARCHAR(50),           -- 来源平台
    hot_score BIGINT,             -- 热度值
    url VARCHAR(1000),            -- 原始链接
    description TEXT,             -- 描述
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### scripts（分镜脚本）
```sql
CREATE TABLE scripts (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER REFERENCES topics(id),
    persona VARCHAR(100),         -- 使用的人设
    scenes_json JSONB,            -- 分镜数据
    model VARCHAR(50),            -- 使用的模型
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### images（图片记录）
```sql
CREATE TABLE images (
    id SERIAL PRIMARY KEY,
    script_id INTEGER REFERENCES scripts(id),
    scene_id INTEGER,             -- 分镜序号
    variant INTEGER,              -- 版本号（1,2,3...）
    path VARCHAR(500),            -- 文件路径
    seed BIGINT,                  -- 生成种子
    prompt TEXT,                  -- 实际使用的 prompt
    selected BOOLEAN DEFAULT FALSE,  -- 是否被选中
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### publishes（发布记录）
```sql
CREATE TABLE publishes (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50),         -- 发布平台
    image_ids INTEGER[],          -- 使用的图片 ID 列表
    caption TEXT,                 -- 发布文案
    status VARCHAR(20),           -- pending/success/failed
    publish_url VARCHAR(1000),    -- 发布后的链接
    error TEXT,                   -- 失败原因
    created_at TIMESTAMP DEFAULT NOW()
);
```

## auto_pipeline.py 命令行参数

```
python auto_pipeline.py [OPTIONS]

必选参数（二选一）：
  --topic TEXT          指定话题（不指定则从热搜采集）
  --step STAGE          只执行指定阶段

可选参数：
  --review              启用人工审核模式
  --variants N          每场景生图版本数（默认 3）
  --platforms LIST      发布平台，逗号分隔（默认从配置读取）
  --config PATH         配置文件路径（默认 pipeline_config.toml）
  --dry-run             试运行，不实际执行发布
  --verbose             详细日志输出

阶段选项（--step）：
  scrape                只采集热点
  script                只生成文案
  images                只生图（需先有脚本）
  publish               只发布（需先有图片）
```