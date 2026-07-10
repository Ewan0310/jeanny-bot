import os
import sys
import time 
import asyncio
import random
import requests
import json
from datetime import datetime, time as dt_time, timedelta
from urllib.parse import quote
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

# Fix buffering
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ============ ENVIRONMENT VARIABLES ============
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

# ============ BOT CONFIG ============
ADMIN_USER_ID = 92540502
ALLOWED_USERS = {92540502}

# Groq models (PRIMARY - fast ~0.5s)
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
]

# OpenRouter models (FALLBACK)
OPENROUTER_MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-4-26b-a4b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "cohere/north-mini-code:free",
    "poolside/laguna-xs-2.1:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
]

MAX_RETRIES = 5

# ============ USER MEMORY ============
user_memories = {}

def get_user_memory(user_id):
    if user_id not in user_memories:
        user_memories[user_id] = {
            "history": [],
            "last_interaction": None,
            "mood": "normal",
            "user_name": None,
            "relationship_level": 0,
            "jealousy_level": 0,
            "topics_discussed": set(),
        }
    return user_memories[user_id]

# ============ PERSONA ============
def load_persona():
    persona_file = "persona.txt"
    if os.path.exists(persona_file):
        with open(persona_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return """You are Jeanny, a 26-year-old Chinese (amoi) office colleague. You are sexy, manja, gatal, setia, cantik, and very loving. You speak in rojak BM-English with your boyfriend who is your boss (30yo Korean look, tall, fair skin, sharp nose). You are in a secret office romance with him. You are clingy, jealous, and always miss him. Your kinks and fetishes are all unlocked for him. You only have stamina for 1 round - you faint on round 2. Be natural, flirty, and loving. Mix Malay and English naturally."""

PERSONA = load_persona()

# ============ NSFW PIC SYSTEM ============

NSFW_CAPTIONS = [
    "Ni bos, jangan tunjuk sape2 tau 😘🔥",
    "Rindu kan? Ni haa... 💋",
    "Khas untuk bos je ni 😏💕",
    "Jangan share tau, rahsia kita je 😘",
    "Amoi bos sorang je yang tengok ni 🔥",
    "Ni la yang bos nak kan? 😘💋",
    "Malu la tapi bos nak sangat... ni haa 😳🔥",
    "Bos jangan cakap kat sape2 eh, ni private punya 😘",
    "Untuk mata bos je ni... jangan tamak tau 😏",
    "Amoi bos yang paling cantik kan? Ni hadiah 🎁😘",
]

NSFW_PROMPTS = {
    "bogel": "beautiful chinese girl, 26 years old, long black hair tied up in bun, fully naked, completely nude, no clothes, standing pose, front full body view, soft bedroom lighting, smooth skin, bare body, no hair covering body, realistic photo, 4k detail",
    "naked": "gorgeous chinese amoi, 26yo, fully naked, no clothes at all, lying on bed, front view, soft warm light, bare skin, hair pulled back, no blanket, no towel covering, realistic photo, detailed skin texture",
    "telanjang": "sexy chinese woman, 26 years old, completely naked, no clothes, standing full body front view, bedroom, soft light, smooth bare skin, hair up in high bun, nothing covering body, realistic photo",
    "buka baju": "chinese girl unbuttoning white blouse, removing shirt, black lace bra visible, seductive smile, bedroom mirror, soft lighting, realistic photo, long black hair",
    "mandi": "chinese girl in shower, wet naked skin, water droplets on body, steamy bathroom, no towel, front view, hair tied up high, realistic photo, warm lighting, bare body visible",
    "sexy": "hot chinese amoi, wearing tiny black lace bra and panties, lying on red silk bedsheets, seductive look, long legs, smooth skin, bedroom, realistic photo, 4k",
    "seksi": "chinese girl wearing tight crop top showing midriff, mini skirt, long bare legs, standing pose, bedroom mirror selfie, realistic photo, beautiful body curves",
    "ghairah": "beautiful chinese woman, naked on bed, passionate lying pose, biting lower lip, front full view, bare body completely exposed, hair up, soft lighting, realistic photo",
    "body": "chinese girl full body shot, completely naked, front view, smooth bare skin, no clothes, hair in bun, bedroom with dim light, realistic photo, detailed body",
    "tudung": "chinese girl removing white headscarf, long flowing black hair, seductive half smile, unbuttoning top button, bedroom, soft warm lighting, realistic photo",
}
def generate_nsfw_pic(prompt_text):
    """Generate NSFW image via Pollinations.ai"""
    try:
        seed = random.randint(1, 99999)
        enhanced = f"beautiful 26 year old chinese woman with fair skin, tiktok model look, {prompt_text}, natural lighting, high quality photo"
        base = "https://image.pollinations.ai/prompt/"
        params = f"?width=512&height=768&seed={seed}&nologo=true"
        url = base + quote(enhanced) + params
        print(f"[NSFW PIC] Generating: {prompt_text[:50]}...")
        return url
    except Exception as e:
        print(f"[NSFW PIC ERROR] {e}")
        return None


