import json
import os
from dataclasses import dataclass


@dataclass
class Config:
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "app_db"
    debug: bool = False
    log_level: str = "INFO"
    pool_size: int = 10


def load_config(source: str = "env", path: str = "config.json") -> Config:
    if source == "env":
        return Config(
            db_host=os.environ.get("DATABASE_HOST", "localhost"),
            db_port=int(os.environ.get("DATABASE_PORT", "5432")),
            db_name=os.environ.get("DATABASE_NAME", "app_db"),
            debug=os.environ.get("DEBUG_MODE", "false").lower() == "true",
        )

    if source == "file":
        with open(path) as f:
            data = json.load(f)
        return Config(
            db_host=data.get("db_host", "localhost"),
            db_port=data.get("db_port", 5432),
            db_name=data.get("db_name", "app_db"),
            debug=data.get("debug", False),
        )

    raise ValueError(f"unknown config source: {source!r}")
