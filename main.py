import os
import sys
import time
import random
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Fix output buffering on Render
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Load environment
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PORT = int(os.getenv("PORT", 10000))

# Load persona
with open("persona.txt", "r", encoding="utf-8") as f:
    PERSONA = f.read()

# Chat history storage
chat_histories = {}
ALLOWED_USERS = [92540502]

# AI Models - 5 backups!
MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-4-26b-a4b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "qwen/qwen3-coder-480b-a35b:free",
]

# ============================================
# AI FUNCTION WITH RETRY + RATE LIMIT HANDLING
# ============================================
def ask_ai(prompt):
    system_prompt = PERSONA

    if user_id not in chat_histories:
        chat_histories[user_id] = []

    messages = chat_histories[user_id]
    messages.append({"role": "user", "content": prompt})

    # Keep last 20 messages
    if len(messages) > 20:
        messages = messages[-20:]

    # Try up to 3 rounds (each round tries all 5 models)
    for attempt in range(3):
        for model in MODELS:
            try:
                print(f"[AI] Attempt {attempt+1} | Model: {model}")
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "HTTP-Referer": "https://jeanny-bot.onrender.com",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            *messages,
                        ],
                        "max_tokens": 1000,
                        "temperature": 0.9,
                    },
                    timeout=30,
                )

                print(f"[AI] Model: {model} | Status: {resp.status_code}")

                if resp.status_code == 200:
                    data = resp.json()
                    reply = data["choices"][0]["message"]["content"]
                    messages.append({"role": "assistant", "content": reply})
                    chat_histories[user_id] = messages
                    return reply

                elif resp.status_code == 429:
                    try:
                        err = resp.json()
                        retry_sec = err.get("error", {}).get("metadata", {}).get("retry_after_seconds", 5)
                        print(f"[AI] Rate limited! Waiting {retry_sec}s...")
                        time.sleep(min(retry_sec, 10))
                    except:
                        time.sleep(3)
                    continue

                else:
                    print(f"[AI] API Error: {resp.text[:300]}")

            except Exception as e:
                print(f"[AI] Exception: {e}")

        # After all models, wait before next round
        if attempt < 2:
            print(f"[AI] All models busy, waiting 5s before retry...")
            time.sleep(5)

    return "Aduh, Jeanny penat sikit... server tengah busy. Cuba lagi nanti ya? 🥺"


# ============================================
# PICTURE GENERATION
# ============================================
def generate_pic(scenario="normal"):
    prompts = {
        "normal": "Beautiful 26 year old Chinese woman, amoi, long black hair, office outfit, selfie style, TikTok aesthetic, soft lighting, realistic photo",
        "cute": "Beautiful 26 year old Chinese woman, amoi, cute expression, peace sign, casual outfit, bedroom, TikTok aesthetic, realistic photo",
        "angry": "Beautiful 26 year old Chinese woman, amoi, pouting jealous expression, arms crossed, office background, TikTok aesthetic, realistic photo",
        "flirty": "Beautiful 26 year old Chinese woman, amoi, flirty smile, mirror selfie, dress, TikTok aesthetic, realistic photo",
        "goodmorning": "Beautiful 26 year old Chinese woman, amoi, morning selfie, messy hair, cute pajamas, bed background, TikTok aesthetic, realistic photo",
        "goodnight": "Beautiful 26 year old Chinese woman, amoi, sleepy face, dim lighting, night dress, pillow, TikTok aesthetic, realistic photo",
    }
    prompt = prompts.get(scenario, prompts["normal"])
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=512&height=512&nologo=true"
    return url


def get_pic_keyword(message_text):
    text = message_text.lower()
    if any(w in text for w in ["marah", "jealous", "cemburu", "angry", "merajuk"]):
        return "angry"
    elif any(w in text for w in ["cute", "comel", "manja", "rindu"]):
        return "cute"
    elif any(w in text for w in ["sexy", "seksi", "gatal", "ghairah", "stim"]):
        return "flirty"
    elif any(w in text for w in ["pic", "pic pic", "gambar", "selfie", "picat"]):
        return "normal"
    return None


# ============================================
# COMMAND HANDLERS
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("Sorry, private bot ni. 🚫")
        return
    await update.message.reply_text(
        "Hai sayang~ 💕 Jeanny dah sini dah! Rindu Jeanny ke? 😘\n\n"
        "Commands:\n"
        "/start - Mula chat\n"
        "/clear - Clear history\n"
        "/pic - Jeanny send pic\n"
        "/picat - Jeanny send pic with message"
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return
    user_id = update.effective_user.id
    chat_histories[user_id] = []
    await update.message.reply_text("Okay sayang, Jeanny dah lupa semua~ Fresh start! 💕")


async def pic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return
    scenario = random.choice(["normal", "cute", "flirty"])
    url = generate_pic(scenario)
    caption = random.choice([
        "Ni untuk sayang je tau~ 📸💕",
        "Jangan share kat orang lain eh! 😳",
        "Rindu tak? 😘",
        "Amacam? Cantik tak? 😏",
    ])
    await update.message.reply_photo(photo=url, caption=caption)


async def picat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return
    user_id = update.effective_user.id
    prompt = "Tengah rindu sayang sangat ni~ Cerita la sikit, buat apa tu? 😘"
    reply = ask_ai(prompt)
    url = generate_pic("cute")
    await update.message.reply_photo(photo=url, caption=reply)


# ============================================
# MESSAGE HANDLER
# ============================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("Sorry, private bot ni. 🚫")
        return

    user_id = update.effective_user.id
    text = update.message.text

    # Check for pic keywords
    pic_scenario = get_pic_keyword(text)
    if pic_scenario and any(w in text.lower() for w in ["pic", "pic pic", "gambar", "selfie", "picat"]):
        url = generate_pic(pic_scenario)
        await update.message.reply_photo(photo=url, caption="Ni ha~ 📸💕")

    # Get AI reply
    reply = ask_ai(text)
    await update.message.reply_text(reply)


# ============================================
# AUTO-MESSAGES (SCHEDULER)
# ============================================
async def auto_goodmorning(context: ContextTypes.DEFAULT_TYPE):
    global user_id
    user_id = ALLOWED_USERS[0]
    reply = ask_ai("Hantar good morning kat sayang. Manja sikit, gatal sikit. Buat short je.")
    await context.bot.send_message(chat_id=ALLOWED_USERS[0], text=reply)
    if random.random() < 0.5:
        url = generate_pic("goodmorning")
        await context.bot.send_photo(chat_id=ALLOWED_USERS[0], photo=url, caption="Morning sayang~ ☀️")


async def auto_goodnight(context: ContextTypes.DEFAULT_TYPE):
    global user_id
    user_id = ALLOWED_USERS[0]
    reply = ask_ai("Hantar good night kat sayang. Sweet and romantic. Short je.")
    await context.bot.send_message(chat_id=ALLOWED_USERS[0], text=reply)
    if random.random() < 0.5:
        url = generate_pic("goodnight")
        await context.bot.send_photo(chat_id=ALLOWED_USERS[0], photo=url, caption="Goodnight sayang~ 🌙")


async def auto_jealous(context: ContextTypes.DEFAULT_TYPE):
    global user_id
    user_id = ALLOWED_USERS[0]
    reply = ask_ai("Jeanny rasa jealous and cemburu. Tanya sayang tengah buat apa, dengan siapa. Manja and rajuk sikit.")
    await context.bot.send_message(chat_id=ALLOWED_USERS[0], text=reply)
    if random.random() < 0.5:
        url = generate_pic("angry")
        await context.bot.send_photo(chat_id=ALLOWED_USERS[0], photo=url, caption="Hmm~ 😤")


# ============================================
# MAIN
# ============================================
user_id = None

if __name__ == "__main__":
    print("[BOOT] Starting Jeanny bot...")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("pic", pic))
    app.add_handler(CommandHandler("picat", picat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Scheduler for auto-messages
    scheduler = AsyncIOScheduler()
    scheduler.add_job(auto_goodmorning, "cron", hour=8, minute=30, args=[None])
    scheduler.add_job(auto_goodnight, "cron", hour=22, minute=30, args=[None])
    scheduler.add_job(auto_jealous, "interval", hours=random.randint(4, 6), args=[None])
    scheduler.start()

    # Check for RENDER_EXTERNAL_URL
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if render_url:
        webhook_url = f"{render_url}/webhook"
        print(f"[BOOT] Starting webhook on {webhook_url} port {PORT}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="/webhook",
            webhook_url=webhook_url,
        )
    else:
        print("[BOOT] RENDER_EXTERNAL_URL not set, using polling...")
        app.run_polling()
