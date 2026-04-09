# =============================================
# Developer : ✘ 𝙍𝘼𝙑𝙀𝙉
# Telegram  : @P_X_24
# =============================================

import json
import os
from config import SUDO_ID

INFO_FILE = "echo_data.json"

def save_info(info_data):
    """Saves the global info dictionary to a JSON file."""
    with open(INFO_FILE, "w", encoding='utf-8') as json_file:
        json.dump(info_data, json_file, indent=4, ensure_ascii=False)

def load_info():
    """Loads the global info dictionary, or initializes it if not found."""
    try:
        with open(INFO_FILE, "r", encoding='utf-8') as json_file:
            info_data = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        info_data = {}

    # Initialize default values
    info_data["sudo"] = SUDO_ID
    info_data.setdefault("admins", {})
    info_data.setdefault("sleeptime", 20)
    info_data.setdefault("bot_mode", "paid")
    info_data.setdefault("vips", {})
    info_data.setdefault("trial_settings", {"enabled": False, "duration_hours": 2})
    info_data.setdefault("trial_users", {})
    
    save_info(info_data)
    return info_data

INFO = load_info()