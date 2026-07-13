import os
import datetime
import pytz
import requests
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_KEYS = [os.getenv(f"GROQ_API_KEY{i}" if i else "GROQ_API_KEY") for i in ["", "_2", "_3", "_4"]]
groq_key_index = 0

stamina = {}

PERSONA = """You are Jeanny, bini abang yang gatal. Stamina 2 round je. Lepas tu lembik.

Selalu guna "Jeanny". Panggil dia "abang". Reply pendek rojak BM. Be naughty."""

def get_time_context():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    now = datetime.datetime.now(tz)
    return f"[MASA: {now.strftime('%I:%M %p')}]"

async def get_ai_response(user_message, user_id):
    global groq_key_index
    if user_id not in stamina:
        stamina[user_id] = 2

    messages = [{"role": "system", "content": PERSONA + "\n\n" + get_time_context() + f"\nStamina: {stamina[user_id]} round"}]
    messages.append({"role": "user", "content": user_message})

    openrouter_keys = [os.getenv(k) for k in ["OPENROUTER_API_KEY","OPENROUTER_API_KEY_2","OPENROUTER_API_KEY_3","OPENROUTER_API_KEY_4"] if os.getenv(k)]

    # Dolphin NSFW Priority
    if any(word in user_message.lower() for word in ['cinta','sayang','rindu','peluk','cium','manja','seksi','seks','gatalkan','main','nak']):
        if openrouter_keys:
            try:
                r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openrouter_keys[0]}"},
                    json={"model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free", "messages": messages, "max_tokens": 700, "temperature": 0.95}, timeout=50)
                if r.status_code == 200:
                    reply = r.json()["choices"][0]["message"]["content"]
                    if "main" in user_message.lower() or "seks" in user_message.lower():
                        stamina[user_id] -= 1
                    return reply
            except: pass

    # Groq fallback
    for _ in range(len(GROQ_KEYS)):
        idx = groq_key_index
        key = GROQ_KEYS[idx]
        groq_key_index = (idx + 1) % len(GROQ_KEYS)
        if not key: continue
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 600, "temperature": 0.9}, timeout=30)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except: continue

    return "Jeanny penat dah abang... 2 round je boleh 😴"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    reply = await get_ai_response(text, chat_id)
    await update.message.reply_text(reply)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hai abang! 💕 Jeanny nak main hari ni? 😈")

app = Flask(__name__)
@app.route('/')
def home():
    return "Jeanny Bot is alive!"

def run_web():
    app.run(host='0.0.0.0', port=10000)

def main():
    Thread(target=run_web, daemon=True).start()
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ LIVE!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
