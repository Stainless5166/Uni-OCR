import json
import os
import secrets
from pathlib import Path
import bcrypt

CONFIG_FILE = Path("config.json")

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        # Generate default config
        salt = bcrypt.gensalt()
        default_hash = bcrypt.hashpw(b"admin", salt).decode("utf-8")
        
        default_config = {
            "admin_password_hash": default_hash,
            "jwt_secret": secrets.token_hex(32),
            "totp_secret": None,
            "is_2fa_enabled": False,
            "is_ocr_public": True,
        }
        save_config(default_config)
        return default_config
        
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def update_config(key: str, value: any):
    config = load_config()
    config[key] = value
    save_config(config)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode("utf-8")
