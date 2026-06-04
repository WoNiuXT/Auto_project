from fastapi import Depends
from app.config import Config

def get_config():
    return Config()
