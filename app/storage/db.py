"""PostgreSQL 数据存储层。

职责：
- 管理连接池
- 提供 topics / scripts / images / publishes 表的 CRUD
- 数据库初始化（建表）
"""
import psycopg2
from typing import Optional


class DB:
    """PostgreSQL 数据访问对象。"""

    def __init__(self, host: str = "127.0.0.1", port: int = 5434,
                 user: str = "pipeline", password: str = "pipeline123",
                 dbname: str = "pipeline"):
        self._dsn = f"host={host} port={port} user={user} password={password} dbname={dbname}"
        self._conn = None

    def connect(self):
        """建立数据库连接。"""
        self._conn = psycopg2.connect(self._dsn)
        self._conn.autocommit = True

    def close(self):
        """关闭连接。"""
        if self._conn:
            self._conn.close()

    def init_tables(self):
        """创建核心表（如不存在）。"""
        sql = """
        CREATE TABLE IF NOT EXISTS topics (
            id SERIAL PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            source VARCHAR(50),
            hot_score BIGINT,
            url VARCHAR(1000),
            description TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS scripts (
            id SERIAL PRIMARY KEY,
            topic_id INTEGER REFERENCES topics(id),
            persona VARCHAR(100),
            scenes_json JSONB,
            model VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS images (
            id SERIAL PRIMARY KEY,
            script_id INTEGER,
            scene_id INTEGER,
            variant INTEGER,
            path VARCHAR(500),
            seed BIGINT,
            prompt TEXT,
            selected BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS publishes (
            id SERIAL PRIMARY KEY,
            platform VARCHAR(50),
            image_ids INTEGER[],
            caption TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            publish_url VARCHAR(1000),
            error TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
        with self._conn.cursor() as cur:
            cur.execute(sql)

    # --- topics ---

    def save_topic(self, title: str, source: str, hot_score: int,
                   url: str = "", description: str = "") -> int:
        """保存热点话题，返回 topic_id。"""
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO topics (title, source, hot_score, url, description) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (title, source, hot_score, url, description)
            )
            return cur.fetchone()[0]

    def topic_exists(self, title: str) -> bool:
        """检查话题是否已存在（去重用）。"""
        with self._conn.cursor() as cur:
            cur.execute("SELECT 1 FROM topics WHERE title = %s LIMIT 1", (title,))
            return cur.fetchone() is not None

    # --- scripts ---

    def save_script(self, topic_id: int, persona: str, scenes_json: dict,
                    model: str = "mimo-v2.5-pro") -> int:
        """保存分镜脚本，返回 script_id。"""
        import json
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO scripts (topic_id, persona, scenes_json, model) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (topic_id, persona, json.dumps(scenes_json, ensure_ascii=False), model)
            )
            return cur.fetchone()[0]

    # --- images ---

    def save_image(self, script_id: int, scene_id: int, variant: int,
                   path: str, seed: int = 0, prompt: str = "") -> int:
        """保存图片记录，返回 image_id。"""
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO images (script_id, scene_id, variant, path, seed, prompt) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (script_id, scene_id, variant, path, seed, prompt)
            )
            return cur.fetchone()[0]

    def mark_image_selected(self, image_id: int):
        """标记图片为已选中。"""
        with self._conn.cursor() as cur:
            cur.execute("UPDATE images SET selected = TRUE WHERE id = %s", (image_id,))

    # --- publishes ---

    def save_publish(self, platform: str, image_ids: list, caption: str,
                     status: str = "pending") -> int:
        """保存发布记录，返回 publish_id。"""
        with self._conn.cursor() as cur:
            cur.execute(
                "INSERT INTO publishes (platform, image_ids, caption, status) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (platform, image_ids, caption, status)
            )
            return cur.fetchone()[0]

    def update_publish_status(self, publish_id: int, status: str,
                              publish_url: str = "", error: str = ""):
        """更新发布状态。"""
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE publishes SET status=%s, publish_url=%s, error=%s WHERE id=%s",
                (status, publish_url, error, publish_id)
            )