# main.py

import os
import json
import requests
import sys
import base64
from datetime import date
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from config import (
    API_KEY,
    BOT_TOKEN,
    MAX_INPUT_LENGTH,
    IMAGE_MAX_AT_ONCE,
    IMAGE_DAILY_LIMIT,
)
from logger import logger

# keep track of user info and selections
STATE_FILE = "state.json"
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        user_state = json.load(f)
else:
    user_state = {}

# stats file for usage tracking
STATS_FILE = "stats.json"
if os.path.exists(STATS_FILE):
    with open(STATS_FILE, "r") as f:
        stats = json.load(f)
else:
    stats = {
        "monthly": {},      # e.g. "2025-05": {"chars": 0, "photos": 0}
        "users": {}         # e.g. "123456": {"total_chars": 0, "total_photos": 0}
    }

def save_stats():
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

# helper function for user display in logs
def get_user_display(user):
    name = user.first_name or 'Unknown'
    username = f'/@{user.username}' if user.username else ''
    return f"{user.id}({name}{username})"

# map your BotFather commands to lang pairs
CMD_LANG = {
    "rus": ("ru", "os"),
    "eng": ("en", "os"),
    "os_en": ("os", "en"),
    "os_ru": ("os", "ru"),
}
CMD_LABEL = {
    "rus": "🇷🇺 Rus → ⬜️🟥🟨 Ossetian",
    "eng": "🇬🇧 Eng → ⬜️🟥🟨 Ossetian",
    "os_en": "⬜️🟥🟨 Ossetian → 🇬🇧 Eng",
    "os_ru": "⬜️🟥🟨 Ossetian → 🇷🇺 Rus",
}

def update_user_state(user):
    uid = str(user.id)
    info = {
        "id":             user.id,
        "is_bot":         user.is_bot,
        "first_name":     user.first_name,
        "last_name":      user.last_name,
        "username":       user.username,
        "language_code":  user.language_code,
        "is_premium":     getattr(user, "is_premium", False),
    }
    if user_state.get(uid) != info:
        user_state[uid] = info
        with open(STATE_FILE, "w") as f:
            json.dump(user_state, f, indent=2)


def log_translation(user_id, length):
    cost = length / 1_000_000 * 20
    logger.info(f"Translated {length} chars for {user_id} | est. cost ${cost:.6f}")

    # update per-month total
    month = date.today().strftime("%Y-%m")
    stats["monthly"].setdefault(month, {"chars": 0, "photos": 0})
    stats["monthly"][month]["chars"] += length

    # update per-user ever-used
    uid = str(user_id)
    stats["users"].setdefault(uid, {"total_chars": 0, "total_photos": 0})
    stats["users"][uid]["total_chars"] += length

    save_stats()

def translate(text, lang_pair):
    src, tgt = lang_pair
    
    resp = requests.post(
        "https://translation.googleapis.com/language/translate/v2",
        data={"q": text, "source": src, "target": tgt, "format": "text", "key": API_KEY},
    )
    if resp.ok:
        result = resp.json()["data"]["translations"][0]["translatedText"]
        return result
    else:
        logger.error(f"Translation API error: {resp.status_code} - {resp.text}")
        return "❗️ Translation error."

async def set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.lstrip("/").split("@")[0]
    user_id = update.effective_user.id
    
    logger.info(f"User {user_id} setting language command: {cmd}")
    
    if cmd in CMD_LANG:
        context.user_data["lang_pair"] = CMD_LANG[cmd]
        logger.info(f"User {user_id} lang_pair set to: {CMD_LANG[cmd]}")
        await update.message.reply_text(
            f"✅ Mode set to: {CMD_LABEL[cmd]}\nNow send text or a photo to translate."
        )
    else:
        logger.warning(f"User {user_id} used unknown command: {cmd}")
        await update.message.reply_text("❗️ Unknown command.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    update_user_state(user)

    if len(text) > MAX_INPUT_LENGTH:
        return await update.message.reply_text(
            f"❗️ Too long. Max is {MAX_INPUT_LENGTH} chars."
        )

    lang_pair = context.user_data.get("lang_pair", ("ru", "os"))
    
    # consolidated logging
    user_info = get_user_display(user)
    logger.info(f"user={user_info} text: {text[:50]} | lang_pair: {lang_pair}")
    
    out = translate(text, lang_pair)

    # consolidated result logging with cost
    cost = len(text) / 1_000_000 * 20
    logger.info(f"user={user_info} result: {out[:50]} | cost: ${cost:.6f}")

    # track usage
    log_translation(user.id, len(text))

    await update.message.reply_text(out)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update_user_state(user)

    photos = update.message.photo or []
    mgid = update.message.media_group_id
    
    user_info = get_user_display(user)
    logger.info(f"photo handler: user={user_info}, media_group_id={mgid}, photo_variants={len(photos)}")

    # enforce daily limit only
    today_str = date.today().isoformat()
    data = context.user_data
    if data.get("image_date") != today_str:
        data["image_date"] = today_str
        data["image_count"] = 0

    if data["image_count"] + 1 > IMAGE_DAILY_LIMIT:
        logger.warning(f"user {user.id} reached daily image limit")
        return await update.message.reply_text(
            f"❗️ Daily image limit reached ({IMAGE_DAILY_LIMIT})"
        )

    # pick highest resolution variant
    photo = photos[-1]
    file = await photo.get_file()
    img_bytes = await file.download_as_bytearray()

    logger.info(f"calling Vision OCR for user={user.id}, bytes={len(img_bytes)}")
    vision_resp = requests.post(
        "https://vision.googleapis.com/v1/images:annotate",
        params={"key": API_KEY},
        json={
            "requests": [{
                "image": {"content": base64.b64encode(img_bytes).decode()},
                "features": [{"type": "TEXT_DETECTION"}]
            }]
        },
    )
    if not vision_resp.ok:
        logger.error(f"OCR error: {vision_resp.text}")
        return await update.message.reply_text("❗️ OCR error.")

    resp0 = vision_resp.json().get("responses", [{}])[0]
    text = resp0.get("fullTextAnnotation", {}).get("text", "").strip()
    if not text:
        logger.info(f"user={user.id} no text detected by OCR")
        return await update.message.reply_text("❗️ No text detected.")

    # log the OCR'd text
    logger.info(f"user={user_info} OCR detected text: {text}")

    lang_pair = data.get("lang_pair", ("ru", "os"))
    logger.info(f"User {user.id} using lang_pair for OCR: {lang_pair}")
    
    translated = translate(text, lang_pair)

    # log the OCR translation
    logger.info(f"user={user_info} OCR translation: {translated}")

    # track photo count
    month = date.today().strftime("%Y-%m")
    stats["monthly"].setdefault(month, {"chars": 0, "photos": 0})
    stats["monthly"][month]["photos"] += 1

    uid = str(user.id)
    stats["users"].setdefault(uid, {"total_chars": 0, "total_photos": 0})
    stats["users"][uid]["total_photos"] += 1

    save_stats()

    data["image_count"] += 1
    log_translation(user.id, len(text))

    await update.message.reply_text(
        f"Detected text:\n{text}\n\nTranslation:\n{translated}"
    )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # register your commands
    app.add_handler(CommandHandler("rus", set_lang))
    app.add_handler(CommandHandler("eng", set_lang))
    app.add_handler(CommandHandler("os_en", set_lang))
    app.add_handler(CommandHandler("os_ru", set_lang))

    # photo handler
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # text handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot started successfully")
    app.run_polling()

if __name__ == "__main__":
    main()
