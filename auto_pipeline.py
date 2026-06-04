"""Auto_pipeline 主编排器。
全自动图文内容生产流水线:
  热点采集 -> AI 文案 -> ComfyUI 生图(多版本) -> [审核] -> 多平台发布
用法:
  python auto_pipeline.py --topic "AI技术发展"             # 全自动
  python auto_pipeline.py --topic "AI技术发展" --review     # 带审核
  python auto_pipeline.py --step scrape                     # 只采集
  python auto_pipeline.py --step script --topic "话题"       # 只文案
  python auto_pipeline.py --step images                     # 只生图
  python auto_pipeline.py --step publish                    # 只发布
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime

from app.config import Config
from app.scrapers.dailyhot import DailyHotScraper
from app.generators.script_gen import ScriptGenerator
from app.generators.image_gen import ImageGenerator
from app.publishers.publisher import Publisher
from app.storage.db import DB


def get_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def step_scrape(config: Config, db: DB, topic: str = None) -> list:
    """阶段一：热点采集。"""
    print("\n=== 阶段一：热点采集 ===")

    if topic:
        print(f"使用指定话题: {topic}")
        topics = [{
            "title": topic,
            "source": "manual",
            "hot_score": 0,
            "url": "",
            "description": "",
        }]
    else:
        dailyhot_cfg = config.section("dailyhot")
        scraper = DailyHotScraper(
            base_url=dailyhot_cfg.get("url", "http://127.0.0.1:6688"),
            platforms=dailyhot_cfg.get("platforms", ["weibo", "zhihu"]),
            max_topics=dailyhot_cfg.get("max_topics", 5),
            exclude_keywords=dailyhot_cfg.get("exclude_keywords", []),
        )
        print(f"采集平台: {scraper.platforms}")
        topics = scraper.fetch_all()
        print(f"采集到 {len(topics)} 条话题")

    # 存入数据库
    for t in topics:
        if not db.topic_exists(t["title"]):
            tid = db.save_topic(t["title"], t["source"], t["hot_score"],
                                t.get("url", ""), t.get("description", ""))
            t["id"] = tid
        else:
            print(f"  跳过重复: {t['title']}")

    return topics


def step_script(config: Config, db: DB, topics: list) -> list:
    """阶段二：AI 文案生成。"""
    print("\n=== 阶段二：AI 文案生成 ===")

    mimo_cfg = config.section("mimo")
    script_cfg = config.section("script")

    gen = ScriptGenerator(
        api_key=config.get("mimo", "api_key"),
        base_url=mimo_cfg.get("base_url", "https://token-plan-cn.xiaomimimo.com/v1"),
        model=mimo_cfg.get("model", "mimo-v2.5-pro"),
        temperature=mimo_cfg.get("temperature", 0.8),
        max_tokens=mimo_cfg.get("max_tokens", 2000),
        proxy=config.proxy,
    )

    scripts = []
    for t in topics:
        print(f"生成文案: {t['title']}")
        result = gen.generate(
            topic=t["title"],
            persona=script_cfg.get("persona", "知识科普博主"),
            scene_count=script_cfg.get("scene_count", 5),
            audience=script_cfg.get("audience", ""),
            tone=script_cfg.get("tone", ""),
        )
        if result:
            # 保存到文件
            ts = get_timestamp()
            safe_title = t["title"][:20].replace(" ", "_").replace("/", "_")
            filename = f"{ts}_{safe_title}_script.json"
            filepath = os.path.join(config.output_dir, filename)
            os.makedirs(config.output_dir, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  保存: {filepath}")

            # 存入数据库
            if "id" in t:
                sid = db.save_script(t["id"], result.get("persona", ""), result)
                result["db_script_id"] = sid

            scripts.append(result)
        else:
            print(f"  [FAIL] {t['title']} 文案生成失败")

    return scripts


def step_images(config: Config, db: DB, scripts: list) -> list:
    """阶段三：ComfyUI 生图。"""
    print("\n=== 阶段三：ComfyUI 生图 ===")

    img_cfg = config.section("image")
    gen = ImageGenerator(
        comfyui_url=img_cfg.get("comfyui_url", "http://127.0.0.1:8188"),
        width=img_cfg.get("width", 1024),
        height=img_cfg.get("height", 1024),
        cfg=img_cfg.get("cfg", 7.0),
        steps=img_cfg.get("steps", 30),
        sampler=img_cfg.get("sampler", "euler_ancestral"),
        scheduler=img_cfg.get("scheduler", "normal"),
        variants=img_cfg.get("variants", 3),
        checkpoint=img_cfg.get("checkpoint", "sd_xl_base_1.0.safetensors"),
    )

    all_images = []
    for script in scripts:
        ts = get_timestamp()
        topic = script.get("topic", "unknown")[:20]
        safe_topic = topic.replace(" ", "_").replace("/", "_")
        out_dir = os.path.join(config.output_dir, f"{ts}_{safe_topic}_images")
        scenes = script.get("scenes", [])
        if not scenes:
            print(f"  [WARN] 无分镜数据，跳过")
            continue

        images = gen.generate_all(scenes, out_dir)
        print(f"  生成 {len(images)} 张图片 -> {out_dir}")
        all_images.extend(images)

        # 存入数据库
        if db:
            for img in images:
                db.save_image(
                    script_id=None,
                    scene_id=img.get("scene_id", 0),
                    variant=img.get("variant", 1),
                    path=img.get("path", ""),
                    seed=img.get("seed", 0),
                    prompt=img.get("prompt", ""),
                )

    return all_images


def step_review(config: Config, images: list) -> list:
    """阶段四：人工审核。"""
    print("\n=== 阶段四：人工审核 ===")

    review_dir = os.path.join(os.path.dirname(config.output_dir), "photo_review")
    os.makedirs(review_dir, exist_ok=True)

    # 按场景分组
    scenes = {}
    for img in images:
        sid = img.get("scene_id", 0)
        if sid not in scenes:
            scenes[sid] = []
        scenes[sid].append(img)

    selected = []
    for scene_id, variants in sorted(scenes.items()):
        print(f"\n场景 {scene_id}:")
        for i, v in enumerate(variants):
            print(f"  v{v.get('variant', i+1)}: {v.get('path', 'N/A')}")

        choice = input(f"  选择版本 (1-{len(variants)}, 0=跳过): ").strip()
        try:
            choice = int(choice)
        except ValueError:
            choice = 0

        if 1 <= choice <= len(variants):
            chosen = variants[choice - 1]
            # 复制到审核目录
            src = chosen.get("path", "")
            if os.path.isfile(src):
                dst = os.path.join(review_dir, os.path.basename(src))
                shutil.copy2(src, dst)
                chosen["review_path"] = dst
            selected.append(chosen)
            print(f"  已选择: v{choice}")
        else:
            print(f"  已跳过")

    return selected


def step_publish(config: Config, db: DB, images: list,
                 platforms: list = None):
    """阶段五：多平台发布。"""
    print("\n=== 阶段五：多平台发布 ===")

    pub_cfg = config.section("publish")
    if not pub_cfg.get("enabled", False) and not platforms:
        print("发布功能未启用，跳过")
        return

    target_platforms = platforms or pub_cfg.get("platforms", ["douyin"])
    publisher = Publisher(
        cookies_dir=config.cookies_dir,
        interval_seconds=pub_cfg.get("interval_seconds", 30),
        max_per_hour=pub_cfg.get("max_per_hour", 5),
    )

    # 准备图片路径列表
    image_paths = [img.get("path", "") for img in images if img.get("path")]
    if not image_paths:
        print("[WARN] 无可用图片，跳过发布")
        return

    # 构建文案（取第一个脚本的描述）
    caption = "AI 自动生成的图文内容"
    hashtags = ["AI", "科技", "知识"]

    results = publisher.publish_all(target_platforms, image_paths, caption, hashtags)
    for r in results:
        print(f"  [{r['platform']}] {r['status']}: {r.get('error', '')}")
        db.save_publish(
            r["platform"],
            [img.get("id", 0) for img in images[:9]],
            caption,
            r["status"],
        )


def main():
    parser = argparse.ArgumentParser(
        description="Auto_pipeline - 全自动图文内容生产流水线"
    )
    parser.add_argument("--topic", "-t", help="指定话题（不指定则从热搜采集）")
    parser.add_argument("--step", "-s", choices=["scrape", "script", "images", "publish"],
                        help="只执行指定阶段")
    parser.add_argument("--review", "-r", action="store_true", help="启用人工审核模式")
    parser.add_argument("--variants", "-v", type=int, help="每场景生图版本数")
    parser.add_argument("--checkpoint", help="ComfyUI checkpoint 模型文件名 (如 v1-5-pruned-emaonly.safetensors 或 sd_xl_base_1.0.safetensors)")
    parser.add_argument("--platforms", "-p", help="发布平台，逗号分隔")
    parser.add_argument("--config", "-c", default="pipeline_config.toml", help="配置文件路径")
    parser.add_argument("--dry-run", action="store_true", help="试运行")
    parser.add_argument("--verbose", action="store_true", help="详细日志")

    args = parser.parse_args()

    # 加载配置
    config = Config(args.config)

    # 覆盖配置
    if args.variants:
        config._data.setdefault("image", {})["variants"] = args.variants

    # 连接数据库
    db = DB(
        port=5434,  # 与 docker-compose.yml 一致
    )
    try:
        db.connect()
        db.init_tables()
    except Exception as e:
        print(f"[WARN] 数据库连接失败: {e}（继续运行，不存储）")
        db = None

    # 执行流水线
    platforms = args.platforms.split(",") if args.platforms else None
    topics = None
    scripts = None
    images = None

    try:
        if args.step:
            # 分步执行
            if args.step == "scrape":
                topics = step_scrape(config, db, args.topic)
                print(f"\n采集结果: {json.dumps(topics, ensure_ascii=False, indent=2)}")

            elif args.step == "script":
                if not args.topic:
                    print("[ERROR] --step script 需要指定 --topic")
                    sys.exit(1)
                topics = [{"title": args.topic, "source": "manual", "hot_score": 0}]
                scripts = step_script(config, db, topics)

            elif args.step == "images":
                # 读取最新的脚本文件
                script_files = sorted([
                    f for f in os.listdir(config.output_dir)
                    if f.endswith("_script.json")
                ])
                if not script_files:
                    print("[ERROR] 未找到分镜脚本文件")
                    sys.exit(1)
                latest = os.path.join(config.output_dir, script_files[-1])
                with open(latest, "r", encoding="utf-8") as f:
                    scripts = [json.load(f)]
                images = step_images(config, db, scripts)

            elif args.step == "publish":
                # 读取最新的 manifest
                manifest_files = []
                for d in os.listdir(config.output_dir):
                    mp = os.path.join(config.output_dir, d, "manifest.json")
                    if os.path.isfile(mp):
                        manifest_files.append(mp)
                if not manifest_files:
                    print("[ERROR] 未找到图片 manifest")
                    sys.exit(1)
                with open(sorted(manifest_files)[-1], "r", encoding="utf-8") as f:
                    images = json.load(f)
                step_publish(config, db, images, platforms)

        else:
            # 完整流水线
            topics = step_scrape(config, db, args.topic)
            if not topics:
                print("没有话题，退出。")
                sys.exit(0)

            scripts = step_script(config, db, topics)
            if not scripts:
                print("文案生成全部失败，退出。")
                sys.exit(1)

            images = step_images(config, db, scripts)
            if not images:
                print("图片生成全部失败，退出。")
                sys.exit(1)

            if args.review:
                selected = step_review(config, images)
            else:
                selected = images  # 自动模式使用全部

            if not args.dry_run:
                step_publish(config, db, selected, platforms)

    finally:
        if db:
            db.close()

    print("\n=== 流水线完成 ===")


if __name__ == "__main__":
    main()