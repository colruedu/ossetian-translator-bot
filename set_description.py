# set_description.py

import requests
import sys
from config import BOT_TOKEN   # ← import directly from your config.py

if not BOT_TOKEN:
    print("Error: BOT_TOKEN not set in config.py")
    sys.exit(1)

NEW_DESCRIPTION = (
    "Ossetian translator for Russian and English – supports text & photo.\n"
    "Default: 🇷🇺 Rus → ⬜️🟥🟨 Ossetian.\n"
    "To switch, tap the menu (☰) any time.\n"
)


def set_bot_description(token: str, description: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/setMyDescription"
    resp = requests.post(url, json={"description": description}, timeout=10)
    data = resp.json()
    if not data.get("ok"):
        print(f"Failed: {data.get('description')}")
        return False
    print("Description updated successfully")
    return True

if __name__ == "__main__":
    set_bot_description(BOT_TOKEN, NEW_DESCRIPTION)
