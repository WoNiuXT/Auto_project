from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
import json
import os
from datetime import datetime

from app.schemas import TopicRequest, ScriptRequest, ImageRequest, ReviewSelect, PublishRequest
from app.database import get_db
from app.dependencies import get_config

from app.scrapers.dailyhot import DailyHotScraper
from app.generators.script_gen import ScriptGenerator
from app.generators.image_gen import ImageGenerator
from app.publishers.publisher import Publisher
from app.storage.db import DB

router = APIRouter()

@router.get("/status")
def get_status():
    return {"status": "running"}

@router.get("/config")
def get_config_endpoint(config = Depends(get_config)):
    return {
        "dailyhot": config.section("dailyhot"),
        "script": config.section("script"),
        "image": {k: v for k, v in config.section("image").items() if k != "api_key"},
    }

@router.post("/scrape")
def scrape_topics(req: TopicRequest, config = Depends(get_config)):
    dailyhot_cfg = config.section("dailyhot")
    scraper = DailyHotScraper(
        platforms=req.platforms or dailyhot_cfg.get("platforms", ["weibo"]),
        max_topics=dailyhot_cfg.get("max_topics", 5),
        exclude_keywords=dailyhot_cfg.get("exclude_keywords", []),
    )
    topics = scraper.fetch_all()
    return {"topics": topics, "count": len(topics)}

@router.post("/script")
def generate_script(req: ScriptRequest, config = Depends(get_config), db: DB = Depends(get_db)):
    gen = ScriptGenerator(
        api_key=config.get("mimo", "api_key"),
        base_url=config.get("mimo", "base_url", "https://token-plan-cn.xiaomimimo.com/v1"),
        model=config.get("mimo", "model", "mimo-v2.5-pro"),
    )
    result = gen.generate(
        topic=req.topic, persona=req.persona, scene_count=req.scene_count,
        audience=req.audience or "", tone=req.tone or "",
    )
    if not result:
        raise HTTPException(status_code=500, detail="Script generation failed")
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = req.topic[:20].replace(" ", "_").replace("/", "_")
    filename = f"{ts}_{safe_title}_script.json"
    filepath = os.path.join(config.output_dir, filename)
    os.makedirs(config.output_dir, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        
    return {"script": result, "path": filepath}

@router.get("/scripts")
def list_scripts(config = Depends(get_config)):
    os.makedirs(config.output_dir, exist_ok=True)
    files = sorted([
        f for f in os.listdir(config.output_dir) if f.endswith("_script.json")
    ])
    return {"scripts": files}

@router.get("/scripts/{filename}")
def get_script(filename: str, config = Depends(get_config)):
    path = os.path.join(config.output_dir, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.post("/images")
def generate_images(req: ImageRequest, config = Depends(get_config)):
    if req.script_path and os.path.isfile(req.script_path):
        with open(req.script_path, "r", encoding="utf-8") as f:
            script = json.load(f)
    else:
        script_files = sorted([
            f for f in os.listdir(config.output_dir) if f.endswith("_script.json")
        ])
        if not script_files:
            raise HTTPException(status_code=404, detail="No scripts found")
        with open(os.path.join(config.output_dir, script_files[-1]), "r", encoding="utf-8") as f:
            script = json.load(f)

    img_cfg = config.section("image")
    gen = ImageGenerator(
        comfyui_url=img_cfg.get("comfyui_url", "http://127.0.0.1:8188"),
        variants=req.variants or img_cfg.get("variants", 3),
        width=img_cfg.get("width", 1024),
        height=img_cfg.get("height", 1024),
    )
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(config.output_dir, f"{ts}_images")
    images = gen.generate_all(script.get("scenes", []), out_dir)
    return {"images": images, "output_dir": out_dir, "count": len(images)}

@router.get("/images")
def list_images(config = Depends(get_config)):
    os.makedirs(config.output_dir, exist_ok=True)
    dirs = []
    for d in sorted(os.listdir(config.output_dir)):
        manifest = os.path.join(config.output_dir, d, "manifest.json")
        if os.path.isfile(manifest):
            with open(manifest, "r", encoding="utf-8") as f:
                images = json.load(f)
            dirs.append({"dir": d, "images": images, "count": len(images)})
    return {"image_dirs": dirs}

@router.post("/review/select")
def review_select(req: ReviewSelect, db: DB = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable")
    with db._conn.cursor() as cur:
        cur.execute(
            "SELECT id, path FROM images WHERE scene_id = %s AND variant = %s ORDER BY id DESC LIMIT 1",
            (req.scene_id, req.selected_variant)
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")
    
    image_id, image_path = row
    with db._conn.cursor() as cur:
        cur.execute("UPDATE images SET selected = FALSE WHERE scene_id = %s", (req.scene_id,))
    db.mark_image_selected(image_id)
    return {"status": "ok", "image_id": image_id, "path": image_path}

@router.post("/publish")
def publish_content(req: PublishRequest, config = Depends(get_config)):
    publisher = Publisher(cookies_dir=config.cookies_dir)
    results = publisher.publish_all(req.platforms, req.image_paths, req.caption)
    return {"results": results}

@router.get("/file")
def serve_file(path: str, config = Depends(get_config)):
    abs_path = os.path.abspath(path)
    abs_output = os.path.abspath(config.output_dir)
    if not abs_path.startswith(abs_output):
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(abs_path)

@router.get("/cookies")
def check_cookies(config = Depends(get_config)):
    publisher = Publisher(cookies_dir=config.cookies_dir)
    platforms = config.section("publish").get("platforms", ["douyin", "bilibili", "xhs"])
    checks = publisher.check_all(platforms)
    return {p: {"valid": ok, "message": msg} for p, (ok, msg) in checks.items()}
