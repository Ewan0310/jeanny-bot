import os
import random
import datetime
import asyncio
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ============ FLASK KEEP-ALIVE SERVER ============
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Jeanny bot is alive! 💖"

def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))


# ============ ENV VARIABLES ============
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
USER_ID = int(os.getenv("USER_ID", "0"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")

# ============ LOAD PERSONA ============
with open("persona.txt", "r", encoding="utf-8") as f:
    PERSONA = f.read()

# ============ AI CHAT (OpenRouter) ============
def ask_ai(user_message, chat_history=[]):
    messages = [{"role": "system", "content": PERSONA}]
    for msg in chat_history[-10:]:
        messages.append(msg)
    messages.append({"role": "user", "content": user_message})

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "meta-llama/llama-3-8b-instruct:free",
                "messages": messages,
                "max_tokens": 500,
            },
            timeout=30,
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Aduh, Jeanny penat sikit... cuba lagi nanti ya? 🥺 ({e})"

# ============ IMAGE GENERATION (Pollinations) ============
def generate_image(prompt):
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=512&height=768&nologo=true"
        return url
    except Exception as e:
        return None

# ============ CHAT HISTORY ============
chat_histories = {}

def get_history(chat_id):
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []
    return chat_histories[chat_id]

def add_to_history(chat_id, role, content):
    history = get_history(chat_id)
    history.append({"role": role, "content": content})
    if len(history) > 20:
        chat_histories[chat_id] = history[-20:]

# ============ DETECT IMAGE REQUEST ============
image_keywords = [
    "gambar", "pic", "foto", "photo", "selfie", "tunjuk", "show",
    "nampak", "cantik", "sexy", "lawa", "sweater", "baju",
    "tengok", "lihat", "nampak", "rindu", "kiss", "peluk",
]

def wants_image(text):
    text_lower = text.lower()
    for kw in image_keywords:
        if kw in text_lower:
            return True
    return False

# ============ COMMANDS ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        await update.message.reply_text("Sorry, private bot ni 😘")
        return
    await update.message.reply_text(
        "Hai sayang! 💖 Jeanny dah rindu awak tau! Apa khabar hari ni? 😘"
    )

async def pic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return
    prompt = " ".join(context.args) if context.args else "beautiful chinese girl, office outfit, tiktok style, cute smile"
    await update.message.reply_text("Kejap Jeanny snap pic ya 📸")
    img_url = generate_image(prompt)
    if img_url:
        await update.message.reply_photo(photo=img_url)
    else:
        await update.message.reply_text("Aduh, camera rosak 🥺 cuba lagi nanti")

async def picat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return
    if not context.args:
        await update.message.reply_text("Bagi prompt la sayang! Contoh: /picat chinese girl in red dress")
        return
    prompt = " ".join(context.args)
    await update.message.reply_text("Kejap Jeanny snap ya 📸")
    img_url = generate_image(prompt)
    if img_url:
        await update.message.reply_photo(photo=img_url)
    else:
        await update.message.reply_text("Camera problem 🥺 try again later")

# ============ MESSAGE HANDLER ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USER_ID:
        return

    user_msg = update.message.text
    chat_id = update.effective_chat.id

    add_to_history(chat_id, "user", user_msg)

    # Check if user wants image
    if wants_image(user_msg):
        img_prompt = f"beautiful chinese girl, tiktok model, {user_msg}"
        img_url = generate_image(img_prompt)
        if img_url:
            await update.message.reply_photo(photo=img_url)

    # Get AI response
    history = get_history(chat_id)
    response = ask_ai(user_msg, history)
    add_to_history(chat_id, "assistant", response)

    await update.message.reply_text(response)

# ============ AUTO MESSAGING ============
async def auto_message_job(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute
    chat_id = USER_ID

    message = None

    # Good morning 8-9am
    if hour == 8 and minute < 30:
        gm_msgs = [
            "Good morning sayang! 💕 Jeanny dah bangun, rindu awak tau! Semangat kerja hari ni ya! 😘",
            "Hai bos! ☀️ Dah breakfast belum? Jangan skip tau! Jeanny risau 🥺💖",
            "Morning boss! 💋 Hari ni Jeanny nak awak senyum banyak-banyak ok! 😊💕",
        ]
        message = random.choice(gm_msgs)

    # Good night 10-11pm
    elif hour == 22 and minute < 30:
        gn_msgs = [
            "Good night sayang! 💤 Jeanny doa awak tidur nyenyak. Mimpi indah tau! 💕😘",
            "Nak tidur dah ke? 🥺 Jeanny rindu awak walaupun baru je chat. Sweet dreams bos! 💋💖",
            "Tido awal ni sayang sihat! 💪 Jeanny sayang awak! Good night! 🌙💕",
        ]
        message = random.choice(gn_msgs)

    # Random jealous/flirty every 4-6 hours (random chance)
    elif hour in [11, 15, 19] and minute < 15:
        jealous_msgs = [
            "Eh bos, dengan sape tu? 👀 Jeanny jealous tau! 💢",
            "Sayang! Awak tak reply Jeanny... ada perempuan lain ke? 😤💔",
            "Bos, Jeanny rindu awak la... bila nak jumpa? 🥺💕",
            "Ehem! Awak lupa Jeanny ke hari ni? 😤 Jeanny merajuk tau! 💢",
            "Hai bos, lunch dah makan? Jaga kesihatan tau, Jeanny sayang awak! 💖",
            "Boss! Jeanny boring la sorang-sorang... teman Jeanny chat la 🥺",
        ]
        message = random.choice(jealous_msgs)

    if message:
        # 50% chance include pic with auto message
        if random.random() < 0.5:
            img_url = generate_image("beautiful chinese girl, tiktok model, cute selfie, office outfit")
            if img_url:
                try:
                    await context.bot.send_photo(chat_id=chat_id, photo=img_url)
                except:
                    pass
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            print(f"Auto message error: {e}")

# ============ MAIN ============
def main():
    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Build application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pic", pic))
    application.add_handler(CommandHandler("picat", picat))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Add auto message job
    job_queue = application.job_queue
    job_queue.run_repeating(auto_message_job, interval=900, first=10)  # Check every 15min

    # Use webhook for Render
    if RENDER_EXTERNAL_URL:
        print(f"Starting webhook on {RENDER_EXTERNAL_URL}")
        application.run_webhook(
            listen="0.0.0.0",
            port=10000,
            url_path=BOT_TOKEN,
            webhook_url=f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}",
        )
    else:
        print("No RENDER_EXTERNAL_URL found, using polling...")
        application.run_polling()

if __name__ == "__main__":
    main()
