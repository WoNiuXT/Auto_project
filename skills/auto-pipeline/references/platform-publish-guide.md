# 多平台发布指南

## 发布架构

采用适配器模式，每个平台一个发布器：

```
publisher.py          # 主发布器，调度各平台
  ├── douyin.py       # 抖音发布
  ├── bilibili.py     # B站发布
  └── xhs.py          # 小红书发布
```

## Cookie 管理

### Cookie 存储位置

```
项目目录/
  cookies/
    douyin.json       # 抖音 Cookie
    bilibili.json     # B站 Cookie
    xhs.json          # 小红书 Cookie
```

### Cookie 获取方法

#### 抖音
1. 浏览器登录 creator.douyin.com
2. F12 -> Application -> Cookies
3. 复制所有 Cookie 到 `cookies/douyin.json`

#### B站
1. 浏览器登录 member.bilibili.com
2. F12 -> Application -> Cookies
3. 复制所有 Cookie 到 `cookies/bilibili.json`

#### 小红书
1. 浏览器登录 creator.xiaohongshu.com
2. F12 -> Application -> Cookies
3. 复制所有 Cookie 到 `cookies/xhs.json`

### Cookie 有效性检查

```powershell
python scripts/check_cookies.py              # 检查所有平台
python scripts/check_cookies.py --platform douyin  # 检查单平台
```

检查原理：用 Cookie 请求一个需要登录的接口，判断返回 200 还是 401/403。

### Cookie 失效处理

- 不自动重试登录（避免账号风控）
- 提示用户："XX 平台 Cookie 已失效，请重新登录后导出"
- 失败的平台跳过，不影响其他平台发布

## 各平台发布参数

### 抖音（creator.douyin.com）

| 参数 | 说明 | 限制 |
|------|------|------|
| 图片 | 1-9 张 | PNG/JPEG, < 20MB/张 |
| 标题 | 视频描述 | ≤ 55 字 |
| 话题 | #话题标签 | 最多 5 个 |
| 定时 | 可选 | 最少 20 分钟后 |

### B站（member.bilibili.com）

| 参数 | 说明 | 限制 |
|------|------|------|
| 图片 | 1-9 张（图文动态） | PNG/JPEG, < 20MB/张 |
| 正文 | 图文描述 | ≤ 2000 字 |
| 话题 | #话题标签 | 最多 10 个 |
| 分区 | 投稿分区 | 需选择合适分区 |

### 小红书（creator.xiaohongshu.com）

| 参数 | 说明 | 限制 |
|------|------|------|
| 图片 | 1-9 张 | PNG/JPEG, 建议 3:4 |
| 标题 | 笔记标题 | ≤ 20 字 |
| 正文 | 笔记内容 | ≤ 1000 字 |
| 话题 | #话题标签 | 最多 10 个 |

## 频率限制策略

```toml
# pipeline_config.toml
[publish]
interval_seconds = 30   # 平台间发布间隔
max_per_hour = 5        # 每平台每小时最大发布数
max_per_day = 20        # 每平台每天最大发布数
```

超限时：排队等待，不报错。超过日限额：停止发布，记录未发布的任务。

## 发布结果记录

每次发布结果写入 PostgreSQL publishes 表：

```json
{
  "platform": "douyin",
  "status": "success",
  "publish_url": "https://www.douyin.com/video/xxx",
  "image_ids": [1, 2, 3],
  "caption": "AI 正在改变世界...",
  "created_at": "2026-06-02T10:30:00Z"
}
```

## 降级策略

| 场景 | 处理 |
|------|------|
| Cookie 失效 | 跳过该平台，记录错误 |
| 网络超时 | 重试 2 次（间隔 5s），仍失败则跳过 |
| 图片格式不支持 | 自动转换为 JPEG 后重试 |
| 频率限制 | 等待后重试 |
| 账号风控 | 立即停止该平台，不重试 |