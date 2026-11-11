from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@lru_cache
def load_config() -> dict:
    cfg = yaml.safe_load((Path(__file__).parent / "config.yaml").read_text())
    if os.environ.get("MODEL_PROFILE"):
        cfg["models"]["profile"] = os.environ["MODEL_PROFILE"]
    if os.environ.get("RAG_VARIANT"):
        cfg["rag"]["variant"] = os.environ["RAG_VARIANT"]
    return cfg


def reload_config() -> dict:
    load_config.cache_clear()
    return load_config()
