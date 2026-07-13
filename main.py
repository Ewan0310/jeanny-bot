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

PERSONA = """You are Jeanny, bini abang yang selalu gatal dan nak main setiap hari.

Stamina: Hanya 1 round je. Lepas tu lembik dan manja.

Selalu guna "Jeanny". Panggil dia "abang". Reply pendek rojak BM. Be naughty."""

def get_time_context():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    now = datetime.datetime.now(tz)
    return f"[MASA: {now.strftime('%I:%M %p')}]"

async def get_ai_response(user_message, user_id):
    global groq_key_index
    messages = [{"role": "system", "content": PERSONA + "\n\n" + get_time_context()}]
    messages.append({"role": "user", "content": user_message})

    for _ in range(len(GROQ_KEYS)):
        idx = groq_key_index
        key = GROQ_KEYS[idx]
        groq_key_index = (idx + 1) % len(GROQ_KEYS)
        if not key: continue
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 400, "temperature": 0.9}, timeout=30)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except: continue

    return "Jeanny penat dah abang... 1 round je boleh 😴"

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
