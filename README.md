# Ossetian Language Translator Bot

A Telegram bot that translates between Ossetian, Russian, and English - handles both text messages and text in photos.

## What it does
- Translates typed messages instantly
- User sends photo with text, bot uses OCR to extract and translate the text
- Supports 4 translation directions
- Tracks daily usage to stay within free API limits

## How to use
Send the bot text or a photo. Default mode translates Russian to Ossetian.

**Switch modes anytime:**
- /rus - Russian → Ossetian  
- /eng - English → Ossetian
- /os_en - Ossetian → English
- /os_ru - Ossetian → Russian

## Setup for developers
You need Google Cloud API key (for translation + vision) and Telegram bot token.

1. `pip install -r requirements.txt`
2. Replace placeholder keys in config.py with real ones
3. `python3 main.py`

**Getting API keys:**
- Google Cloud: https://console.cloud.google.com/apis/library/translate.googleapis.com
  - Enable Translation + Vision APIs
  - Create API key in Credentials
  - Free: 500k chars/month translation + 1k images/month
  - Paid: $20/million chars + $1.50/1k images
- Telegram: Message @BotFather to create bot token

**Cost management:** Set quotas in Google Cloud Console to avoid surprise bills.

## Features
- Daily limits: 500 chars text, 20 photos
- Usage statistics tracking
- Automatic file creation (logs, stats, state)
- Error handling and logging
