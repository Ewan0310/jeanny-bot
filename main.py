# ============================================
# 📦 JEANNY BOT - 4 GROQ + DOLPHIN NSFW
# ============================================
import os
import httpx
import datetime
import pytz
import requests
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============================================
# 🔑 API KEYS
# ============================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Groq 4 keys
GROQ_KEYS = [
    os.getenv("GROQ_API_KEY"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3"),
    os.getenv("GROQ_API_KEY_4"),
]
groq_key_index = 0

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
FAL_API_KEY = os.getenv("FAL_API_KEY")
ADMIN_USER_ID = 92540502

conversation_histories = {}
MAX_HISTORY = 20

GEMINI_KEYS = [os.getenv(f"GEMINI_API_KEY{i}" if i else "GEMINI_API_KEY") for i in ["","_2","_3","_4"]]
gemini_key_index = 0


def get_history(chat_id): 
    if chat_id not in conversation_histories: conversation_histories[chat_id] = []
    return conversation_histories[chat_id]

def add_to_history(chat_id, role, content):
    history = get_history(chat_id)
    history.append({"role": role, "content": content})
    if len(history) > MAX_HISTORY: conversation_histories[chat_id] = history[-MAX_HISTORY:]


try:
    with open("persona.txt", "r", encoding="utf-8") as f:
        PERSONA = f.read().strip()
except:
    PERSONA = "You are Jeanny, a friendly Malaysian girl who is manja and playful."


def get_time_context():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    now = datetime.datetime.now(tz)
    hour = now.hour
    day = now.strftime("%A")
    is_weekend = day in ["Saturday", "Sunday"]
    # ... (sama macam sebelum ni, aku shorten)
    period = "malam weekend - masa intimate" if is_weekend and hour >= 18 else "pagi pejabat" if 9 <= hour < 12 else "malam - masa kita"
    return f"[MASA SEKARANG: {now.strftime('%I:%M %p')}, {day}, {period}]"


# ============================================
# AI RESPONSE - 4 GROQ + DOLPHIN NSFW
# ============================================
async def get_ai_response(user_message: str, user_id: int):
    global groq_key_index, gemini_key_index
    system_prompt = PERSONA
    if user_id == ADMIN_USER_ID:
        system_prompt += "\n\n[ADMIN MODE: Extra care for abang.]"

    history = get_history(user_id)
    time_ctx = get_time_context()

    nsfw_triggers = ['cinta','sayang','rindu','peluk','cium','manja','syg','baby','love','kiss','hug','romantik','stim','ghairah','seksi','raba','usap','buka baju','tilam','bilik','badan','montok','bogel','telanjang','seks','puas','gatalkan']
    is_nsfw = any(word in user_message.lower() for word in nsfw_triggers)

    messages = [{"role": "system", "content": f"{system_prompt}\n\n[TIME: {time_ctx}]"}]
    if is_nsfw:
        messages.append({"role": "system", "content": "Jeanny is feeling very flirty, naughty and playful. Match abang's energy."})

    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    openrouter_keys = [os.getenv(k) for k in ["OPENROUTER_API_KEY","OPENROUTER_API_KEY_2","OPENROUTER_API_KEY_3","OPENROUTER_API_KEY_4"] if os.getenv(k)]

    # === NSFW PRIORITY: DOLPHIN ===
    if is_nsfw and openrouter_keys:
        print("[NSFW] Using Dolphin Venice...")
        try:
            r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {openrouter_keys[0]}"},
                json={"model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free", "messages": messages, "max_tokens": 700, "temperature": 0.9},
                timeout=40)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except: pass

    # === Groq 4 Keys Rotate ===
    for _ in range(len(GROQ_KEYS)):
        idx = groq_key_index
        key = GROQ_KEYS[idx]
        groq_key_index = (idx + 1) % len(GROQ_KEYS)
        if not key: continue
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 700, "temperature": 0.75}, timeout=30)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except: continue

    # Gemini, Together, OpenRouter fallback (sama macam sebelum)
    # ... (untuk jimat space, boleh copy dari version sebelum ni)

    return "Abang... Jeanny penat sikit 😔 Try lagi ya sayang 💕"


# (Bahagian generate_image, handlers, main — sama macam full code sebelum ni)

# ============================================
# MAIN
# ============================================
app = Flask(__name__)
@app.route('/') 
def home(): return "Jeanny Bot Running 💕"

def run_web(): app.run(host='0.0.0.0', port=10000, debug=False)

def main():
    print("🚀 Jeanny Bot Starting...")
    Thread(target=run_web, daemon=True).start()
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ LIVE!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
