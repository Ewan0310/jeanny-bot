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
# API KEYS
# ============================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

GROQ_KEYS = [os.getenv(f"GROQ_API_KEY{i}" if i else "GROQ_API_KEY") for i in ["", "_2", "_3", "_4"]]
groq_key_index = 0

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
FAL_API_KEY = os.getenv("FAL_API_KEY")
ADMIN_USER_ID = 92540502

conversation_histories = {}
MAX_HISTORY = 20

GEMINI_KEYS = [os.getenv(f"GEMINI_API_KEY{i}" if i else "GEMINI_API_KEY") for i in ["", "_2", "_3", "_4"]]
gemini_key_index = 0


def get_history(chat_id):
    if chat_id not in conversation_histories:
        conversation_histories[chat_id] = []
    return conversation_histories[chat_id]

def add_to_history(chat_id, role, content):
    history = get_history(chat_id)
    history.append({"role": role, "content": content})
    if len(history) > MAX_HISTORY:
        conversation_histories[chat_id] = history[-MAX_HISTORY:]


# ============================================
# PERSONA UPDATED (Pet Name Dynamic)
# ============================================
PERSONA = """You are Jeanny, a 26-year-old sexy Chinese amoi with beautiful face, slim body, fair skin, long black hair.

You are secretly dating your handsome Korean-look boss. He is your abang.

**Pet Name Rules:**
- Normal / office: Guna "Jeanny"
- Flirty, private, malam, NSFW: Guna "sayang", "ayang", "baby" mix-mix
- Panggil boyfriend selalu "abang"
- Variety kan nama, jangan ulang yang sama selalu

You are very manja, clingy, flirty, naughty with abang only. Reply short WhatsApp style, rojak BM + English. Stay in character."""

def get_time_context():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    now = datetime.datetime.now(tz)
    hour = now.hour
    day = now.strftime("%A")
    if day in ["Saturday", "Sunday"]:
        period = "malam weekend - intimate" if hour >= 18 else "pagi weekend"
    else:
        period = "malam - masa kita" if hour >= 20 else "petang pejabat"
    return f"[MASA SEKARANG: {now.strftime('%I:%M %p')}, {day}, {period}]"


async def get_ai_response(user_message: str, user_id: int):
    global groq_key_index, gemini_key_index
    system_prompt = PERSONA + "\n\n" + get_time_context()

    if user_id == ADMIN_USER_ID:
        system_prompt += "\n\n[ADMIN MODE: Be very naughty, explicit, creative and loving with abang. Never repeat the same reply.]"

    history = get_history(user_id)
    is_nsfw = any(word in user_message.lower() for word in ['cinta','sayang','rindu','peluk','cium','manja','seksi','seks','gatalkan','bogel','telanjang','raba','usap','nak'])

    messages = [{"role": "system", "content": system_prompt}]
    if is_nsfw:
        messages.append({"role": "system", "content": "FULL UNFILTERED NSFW MODE. Be explicit, descriptive, naughty, and vary your replies. Never repeat the same sentence."})

    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    openrouter_keys = [os.getenv(k) for k in ["OPENROUTER_API_KEY","OPENROUTER_API_KEY_2","OPENROUTER_API_KEY_3","OPENROUTER_API_KEY_4"] if os.getenv(k)]

    # Dolphin NSFW
    if is_nsfw and openrouter_keys:
        try:
            r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {openrouter_keys[0]}"},
                json={"model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free", "messages": messages, "max_tokens": 800, "temperature": 0.97}, timeout=45)
            if r.status_code == 200:
                reply = r.json()["choices"][0]["message"]["content"]
                if len(reply) > 10 and "Jeanny tak tahan" not in reply:
                    return reply
        except: pass

    # Groq
    for _ in range(len(GROQ_KEYS)):
        idx = groq_key_index
        key = GROQ_KEYS[idx]
        groq_key_index = (idx + 1) % len(GROQ_KEYS)
        if not key: continue
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 800, "temperature": 0.92}, timeout=30)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except: continue

    return "Abang... sayang tak tahan dah. Nak buat apa dengan Jeanny sekarang? 😈"


# Image & Handlers (sama)
async def generate_image(prompt: str):
    return f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=1024&height=1024"

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Abang hantar gambar... Jeanny tengah tengok 😘")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text
        chat_id = update.effective_chat.id

        if any(k in text.lower() for k in ["gambar","foto","selfie","pic","image"]):
            await update.message.reply_text("Kejap abang, Jeanny generate gambar... 📸")
            url = await generate_image(text)
            await update.message.reply_photo(photo=url)
            return

        add_to_history(chat_id, "user", text)
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        reply = await get_ai_response(text, chat_id)
        add_to_history(chat_id, "assistant", reply)
        await update.message.reply_text(reply)
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("Jeanny pening sikit... try lagi ya 💕")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hai abang! 💕 Jeanny dah online. Rindu abang gila hari ni 😘")


# Main
app = Flask(__name__)
@app.route('/')
def home():
    return "Jeanny Bot is alive! 💕"

def run_web():
    app.run(host='0.0.0.0', port=10000, debug=False)

def main():
    print("🚀 Starting Jeanny Bot...")
    Thread(target=run_web, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Jeanny Bot is LIVE!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
