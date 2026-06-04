from pydantic import BaseModel
from typing import Optional, List

class TopicRequest(BaseModel):
    topic: Optional[str] = None
    platforms: Optional[list] = None

class ScriptRequest(BaseModel):
    topic: str
    persona: str = "default_persona"
    scene_count: int = 5
    audience: str = ""
    tone: str = ""

class ImageRequest(BaseModel):
    script_path: Optional[str] = None
    variants: int = 3

class ReviewSelect(BaseModel):
    scene_id: int
    selected_variant: int

class PublishRequest(BaseModel):
    platforms: list = ["douyin"]
    image_paths: list = []
    caption: str = ""
