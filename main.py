# ============================================
# 📦 SECTION 1: IMPORTS
# ============================================
import os
import httpx
import datetime
import pytz
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ============================================
# 🔑 SECTION 2: API KEYS & CONFIG
# ============================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
FAL_API_KEY = os.getenv("FAL_API_KEY")

# ============================================
# 📄 SECTION 3: LOAD PERSONA (persona.txt)
# ============================================
# Ni file persona.txt yang ko upload kat GitHub
# Kalau takde, guna default
try:
    with open("persona.txt", "r", encoding="utf-8") as f:
        PERSONA = f.read()
except FileNotFoundError:
    PERSONA = "You are Jeanny, a friendly Malaysian girl."

# ============================================
# 🕐 SECTION 4: TIME AWARENESS
# ============================================
# Ni yang bagi tau bot masa sekarang (Malaysia timezone)
def get_time_context():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    now = datetime.datetime.now(tz)
    hour = now.hour
    day = now.strftime("%A")
    is_weekend = day in ["Saturday", "Sunday"]

    if is_weekend:
        if 7 <= hour < 12:
            period = "pagi weekend - abang santai kat rumah"
        elif 12 <= hour < 18:
            period = "tengahari weekend - abang keluar jalan"
        elif 18 <= hour < 21:
            period = "petang weekend - abang balik rumah dah"
        else:
            period = "malam weekend - masa intimate"
    else:
        if 7 <= hour < 9:
            period = "pagi weekdays - abang baru bangun/siap pergi kerja"
        elif 9 <= hour < 12:
            period = "pagi pejabat - abang tengah kerja, busy"
        elif 12 <= hour < 14:
            period = "tengahari - waktu lunch abang"
        elif 14 <= hour < 18:
            period = "petang pejabat - abang tengah kerja"
        elif 18 <= hour < 20:
            period = "petang - abang baru habis kerja/traffic"
        elif 20 <= hour < 23:
            period = "malam - abang kat rumah, masa kita"
        else:
            period = "larut malam - abang nak tidur dah"

    return f"[MASA SEKARANG: {now.strftime('%I:%M %p')}, {day}, {period}]"

# ============================================
# 🤖 SECTION 5: AI RESPONSE (TEXT CHAT)
# ============================================
# Ni function yang hantar mesej ke Groq/OpenRouter dan dapat balasan
async def get_ai_response(user_message: str) -> str:
    time_context = get_time_context()

    # Combine persona + time + user message
    full_prompt = f"{PERSONA}\n\n{time_context}\n\nUser: {user_message}"

    # Try Groq first (PRIMARY - free & fast)
    if GROQ_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": PERSONA},
                            {"role": "system", "content": time_context},
                            {"role": "user", "content": user_message},
                        ],
                        "max_tokens": 1024,
                        "temperature": 0.8,
                    },
                )
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[GROQ ERROR] {e}")

    # Try OpenRouter (FALLBACK)
    if OPENROUTER_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "openai/gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": PERSONA},
                            {"role": "system", "content": time_context},
                            {"role": "user", "content": user_message},
                        ],
                        "max_tokens": 1024,
                        "temperature": 0.8,
                    },
                )
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[OPENROUTER ERROR] {e}")

    return "Ehh abang, Jeanny tengah pening sat... try lagi eh 💕"

# ============================================
# 🖼️ SECTION 6: IMAGE GENERATION (NSFW)
# ============================================
# Ni function generate gambar guna fal.ai / Together.ai / Pollinations
async def generate_image(prompt: str) -> str:
    # Try fal.ai first (PRIMARY - uncensored)
    if FAL_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://fal.run/fal-ai/flux/schnell",
                    headers={
                        "Authorization": f"Key {FAL_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={"prompt": prompt},
                )
                data = response.json()
                if "images" in data:
                    return data["images"][0]["url"]
                if "output" in data:
                    return data["output"][0] if isinstance(data["output"], list) else data["output"]
        except Exception as e:
            print(f"[FAL ERROR] {e}")

    # Try Together.ai (FALLBACK)
    if TOGETHER_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://api.together.xyz/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {TOGETHER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "black-forest-labs/FLUX.1-schnell-Free",
                        "prompt": prompt,
                        "width": 1024,
                        "height": 1024,
                        "steps": 4,
                    },
                )
                data = response.json()
                return data["data"][0]["url"]
        except Exception as e:
            print(f"[TOGETHER ERROR] {e}")

    # Pollinations (LAST RESORT - SFW)
    try:
        encoded = prompt.replace(" ", "%20")
        return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024"
    except:
        return None

# ============================================
# 📸 SECTION 7: PHOTO HANDLER (VISION)
# ============================================
# Ni handle bila user hantar GAMBAR ke bot
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_url = file.file_path

        caption = update.message.caption or "Describe this photo"

        # Try gpt-4o-mini vision (PRIMARY)
        if OPENROUTER_API_KEY:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "openai/gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": PERSONA},
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": caption},
                                    {"type": "image_url", "image_url": {"url": image_url}},
                                ],
                            },
                        ],
                        "max_tokens": 512,
                    },
                )
                data = response.json()
                reply = data["choices"][0]["message"]["content"]
                await update.message.reply_text(reply)
                return

        await update.message.reply_text("Ehh abang, Jeanny tak nampak gambar tu la 😅")

    except Exception as e:
        print(f"[PHOTO ERROR] {e}")
        await update.message.reply_text("Gambar tu blur la abang, try lagi eh!")

# ============================================
# 💬 SECTION 8: TEXT MESSAGE HANDLER
# ============================================
# Ni handle semua mesej teks dari user
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_message = update.message.text

        # Check kalau user nak gambar
        image_keywords = ["gambar", "foto", "picture", "selfie", "pic", "image", "nampak"]
        if any(word in user_message.lower() for word in image_keywords):
            await update.message.reply_text("Kejap eh abang, Jeanny nak generate gambar... 📸")
            image_url = await generate_image(user_message)
            if image_url:
                await update.message.reply_photo(photo=image_url)
            else:
                await update.message.reply_text("Ehh tak jadi la abang, try lain eh 😅")
            return

        # Normal text chat
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        reply = await get_ai_response(user_message)
        await update.message.reply_text(reply)

    except Exception as e:
        print(f"[MESSAGE ERROR] {e}")
        await update.message.reply_text("Ehh abang, Jeanny pening sat... try lagi eh 💕")

# ============================================
# 🚀 SECTION 9: START COMMAND
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hai abang! 💕 Jeanny dah sini. Nak borak dengan Jeanny ke? 😘"
    )

# ============================================
# 🌐 SECTION 10: WEB SERVER (KEEP RENDER ALIVE)
# ============================================
# Ni supaya Render tak restart bot ko
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "Jeanny Bot is alive! 💕"

def run_web():
    app_web.run(host="0.0.0.0", port=10000)

# ============================================
# ▶️ SECTION 11: MAIN - START BOT
# ============================================
def main():
    print("[BOOT] Starting Jeanny Bot...")

    # Start web server in background thread
    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()
    print("[BOOT] Web server started on port 10000 ✅")

    # Start Telegram bot
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))  # PHOTO FIRST!
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("[BOOT] Jeanny Bot is LIVE! 💕")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
