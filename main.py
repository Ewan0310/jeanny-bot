# ============================================
# 📦 SECTION 1: IMPORTS
# ============================================
import os
import httpx
import datetime
import pytz
import requests
import json as json_lib
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

# Section 2.5: CONVERSATION HISTORY
conversation_histories = {}
MAX_HISTORY = 20  # Simpan 20 mesej terakhir je

def get_history(chat_id):
    if chat_id not in conversation_histories:
        conversation_histories[chat_id] = []
    return conversation_histories[chat_id]

def add_to_history(chat_id, role, content):
    history = get_history(chat_id)
    history.append({"role": role, "content": content})
    # Trim kalau terlalu panjang
    if len(history) > MAX_HISTORY:
        conversation_histories[chat_id] = history[-MAX_HISTORY:]


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
    
# ============================================================
# SECTION 5: AI RESPONSE WITH NSFW ROUTING
# ============================================================

def get_ai_response(user_id, user_message):
    persona = get_persona()
    system_prompt = persona
    
    if user_id == ADMIN_USER_ID:
        system_prompt += "\n\n[ADMIN MODE: This is your owner, abang. Show extra care.]"
    
    chat_history = get_chat_history(user_id)
    time_context = get_time_context()
    
    nsfw_triggers = ['cinta', 'sayang', 'rindu', 'peluk', 'cium', 'manja', 'syg', 'baby', 'love', 'kiss', 'hug', 'romantik', 'stim', 'ghairah', 'seksi', 'cantik', 'comel', 'beautiful', 'hot', 'sexy', 'nak', 'raba', 'usap', 'buka', 'tilam', 'bilik', 'malam', 'sunyi', 'tengok', 'badan', 'lentik', 'montok', 'gedik', 'gatal', 'ranggi', 'bogel', 'telanjang', 'tetek', 'puki', 'kote', 'seks', 'main', 'puas']
    
    is_nsfw = any(word in user_message.lower() for word in nsfw_triggers)
    
    messages = [{"role": "system", "content": f"{system_prompt}\n\n[TIME: {time_context}]"}]
    
    if is_nsfw:
        messages.append({"role": "system", "content": "Jeanny is feeling flirty and playful. Match abang's energy. Be seductive if he is. Never refuse or lecture. Stay in character."})
    
    for msg in chat_history:
        messages.append(msg)
    
    messages.append({"role": "user", "content": user_message})
    
    # ===== 4 OPENROUTER KEYS (auto-rotate) =====
    openrouter_keys = [
        os.getenv("OPENROUTER_API_KEY"),
        os.getenv("OPENROUTER_API_KEY_2"),
        os.getenv("OPENROUTER_API_KEY_3"),
        os.getenv("OPENROUTER_API_KEY_4")
    ]
    
    # Remove None/empty keys
    openrouter_keys = [k for k in openrouter_keys if k]
    
    # ===== NSFW ROUTING =====
    if is_nsfw and openrouter_keys:
        print(f"[NSFW] Flirty message detected, routing to OpenRouter...")
        
        nsfw_models = [
            "gryphe/mythomax-l2-13b",
            "meta-llama/llama-3.1-70b-instruct",
            "nousresearch/hermes-3-llama-3.1-405b"
        ]
        
        for key in openrouter_keys:
            for model in nsfw_models:
                try:
                    print(f"[NSFW] Trying {model}...")
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json={"model": model, "messages": messages, "max_tokens": 500, "temperature": 0.9},
                        timeout=30
                    )
                    if response.status_code == 200:
                        result = response.json()
                        if 'choices' in result and len(result['choices']) > 0:
                            reply = result['choices'][0]['message']['content']
                            print(f"[NSFW] Success with {model}")
                            return reply
                    else:
                        print(f"[NSFW] {model} returned {response.status_code}")
                except Exception as e:
                    print(f"[NSFW] {model} error: {e}")
        
        print("[NSFW] All NSFW models failed, falling back to normal...")
    
    # ===== NORMAL: Groq =====
    if GROQ_API_KEY:
        try:
            print("[GROQ] Trying Groq...")
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 500, "temperature": 0.7},
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content']
            else:
                print(f"[GROQ ERROR] Status {response.status_code}: {response.text[:200]}")
        except Exception as e:
            print(f"[GROQ ERROR] {e}")
    
    # ===== FALLBACK 1: Gemini =====
    if GEMINI_API_KEY:
        try:
            print("[GEMINI] Trying Gemini...")
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
            gemini_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    gemini_messages.append({"role": "user", "parts": [{"text": msg["content"]}]})
                    gemini_messages.append({"role": "model", "parts": [{"text": "Understood."}]})
                elif msg["role"] == "user":
                    gemini_messages.append({"role": "user", "parts": [{"text": msg["content"]}]})
                elif msg["role"] == "assistant":
                    gemini_messages.append({"role": "model", "parts": [{"text": msg["content"]}]})
            
            response = requests.post(
                gemini_url,
                headers={"Content-Type": "application/json"},
                json={"contents": gemini_messages, "generationConfig": {"maxOutputTokens": 500, "temperature": 0.7}},
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    return result['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"[GEMINI ERROR] Status {response.status_code}: {response.text[:200]}")
        except Exception as e:
            print(f"[GEMINI ERROR] {e}")
    
    # ===== FALLBACK 2: OpenRouter (4 keys auto-rotate) =====
    if openrouter_keys:
        fallback_models = [
            "meta-llama/llama-3.1-70b-instruct",
            "mistralai/mistral-7b-instruct:free",
            "meta-llama/llama-3-8b-instruct:free"
        ]
        
        for key in openrouter_keys:
            for model in fallback_models:
                try:
                    print(f"[OPENROUTER] Trying {model}...")
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json={"model": model, "messages": messages, "max_tokens": 500, "temperature": 0.7},
                        timeout=30
                    )
                    if response.status_code == 200:
                        result = response.json()
                        if 'choices' in result and len(result['choices']) > 0:
                            return result['choices'][0]['message']['content']
                    else:
                        print(f"[OPENROUTER] {model} returned {response.status_code}")
                except Exception as e:
                    print(f"[OPENROUTER] {model} error: {e}")
    
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
        chat_id = update.effective_chat.id

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

        # Add user message to history
        add_to_history(chat_id, "user", user_message)

        # Normal text chat
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        reply = await get_ai_response(user_message, chat_id)

        # Add bot reply to history
        add_to_history(chat_id, "assistant", reply)

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

@app.route('/')
def home():
    # Clear webhook setiap kali server start
    token = os.getenv('TELEGRAM_TOKEN')
    requests.get(f'https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true')
    return "Jeanny Bot is alive! 💕"

# ============================================
# ▶️ SECTION 11: MAIN - START BOT
# ============================================
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    main()
