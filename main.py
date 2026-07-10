import os
import sys
import random
import requests
from datetime import time as dt_time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ============ CONFIG ============
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OWNER_ID = 92540502
PORT = int(os.environ.get("PORT", 10000))

MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-4-26b-a4b-it:free",
]

with open("persona.txt", "r", encoding="utf-8") as f:
    PERSONA = f.read()

chat_histories = {}

# ============ AI FUNCTION ============
def ask_ai(user_id, user_message):
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    chat_histories[user_id].append({"role": "user", "content": user_message})
    chat_histories[user_id] = chat_histories[user_id][-20:]
    messages = [{"role": "system", "content": PERSONA}] + chat_histories[user_id]

    for model in MODELS:
        try:
            print(f"[AI] Trying model: {model}", flush=True)
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://jeanny-bot.onrender.com",
                },
                json={"model": model, "messages": messages},
                timeout=30,
            )
            print(f"[AI] Model: {model} | Status: {response.status_code}", flush=True)
            if response.status_code != 200:
                print(f"[AI] Error: {response.text[:500]}", flush=True)
                continue
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                reply = data["choices"][0]["message"]["content"]
                chat_histories[user_id].append({"role": "assistant", "content": reply})
                print(f"[AI] SUCCESS with {model}", flush=True)
                return reply
            else:
                print(f"[AI] No choices: {str(data)[:300]}", flush=True)
                continue
        except Exception as e:
            print(f"[AI] Exception: {e}", flush=True)
            continue

    return "Aduh, Jeanny penat sikit... server tengah busy. Cuba lagi nanti ya? 🥺"

# ============ IMAGE FUNCTION ============
def generate_image(prompt):
    try:
        url = f"https://image.pollinations.ai/prompt/{prompt}?width=512&height=768&nologo=true"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f"[IMAGE] Error: {e}", flush=True)
    return None

def has_pic_keyword(text):
    keywords = ["pic", "gambar", "selfie", "photo", "foto"]
    return any(kw in text.lower() for kw in keywords)

# ============ AUTO-MESSAGES ============
async def good_morning(context: ContextTypes.DEFAULT_TYPE):
    msg = ask_ai(OWNER_ID, "(System: Generate a sweet good morning message for your boss. Short and flirty. In rojak BM-English.)")
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=msg)
    except Exception as e:
        print(f"[AUTO] Morning error: {e}", flush=True)
    if random.random() < 0.5:
        img = generate_image("beautiful chinese girl selfie good morning smile")
        if img:
            try:
                await context.bot.send_photo(chat_id=OWNER_ID, photo=img)
            except:
                pass

async def good_night(context: ContextTypes.DEFAULT_TYPE):
    msg = ask_ai(OWNER_ID, "(System: Generate a sweet good night message for your boss. Short, romantic, manja. In rojak BM-English.)")
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=msg)
    except Exception as e:
        print(f"[AUTO] Night error: {e}", flush=True)
    if random.random() < 0.5:
        img = generate_image("beautiful chinese girl good night cute pajamas")
        if img:
            try:
                await context.bot.send_photo(chat_id=OWNER_ID, photo=img)
            except:
                pass

async def jealousy_check(context: ContextTypes.DEFAULT_TYPE):
    msg = ask_ai(OWNER_ID, "(System: Generate a short jealous/possessive check-in message to your boss. Like asking where he is, who he's with. Manja and clingy. In rojak BM-English.)")
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=msg)
    except Exception as e:
        print(f"[AUTO] Jealousy error: {e}", flush=True)
    if random.random() < 0.5:
        img = generate_image("beautiful chinese girl pouting jealous cute selfie")
        if img:
            try:
                await context.bot.send_photo(chat_id=OWNER_ID, photo=img)
            except:
                pass

# ============ HANDLERS ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text("Sorry, private bot ni je. 🙈")
        return
    reply = ask_ai(uid, "(User started the bot. Greet him warmly as Jeanny.)")
    await update.message.reply_text(reply)

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        return
    chat_histories[uid] = []
    await update.message.reply_text("Chat history cleared! Fresh start~ 🔄")

async def pic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        return
    prompt = " ".join(context.args) if context.args else "beautiful chinese girl selfie smile"
    await update.message.reply_text("Tunggu jap, Jeanny snap pic... 📸")
    img = generate_image(prompt)
    if img:
        await update.message.reply_photo(photo=img)
    else:
        await update.message.reply_text("Aduh, pic tak dapat generate. Cuba lagi? 😅")

async def picat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        return
    full = " ".join(context.args)
    parts = full.split("|", 1)
    if len(parts) < 2:
        await update.message.reply_text("Guna format: /picat situation | outfit\nContoh: /picat kat office | baju kurung ketat")
        return
    prompt = f"beautiful chinese girl {parts[0].strip()} wearing {parts[1].strip()}, selfie, realistic"
    await update.message.reply_text("Kejap, Jeanny prepare dulu... 📸")
    img = generate_image(prompt)
    if img:
        await update.message.reply_photo(photo=img)
    else:
        await update.message.reply_text("Pic tak jadi. Cuba lagi nanti? 😅")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        return
    text = update.message.text
    if has_pic_keyword(text):
        img = generate_image("beautiful chinese girl selfie cute smile")
        if img:
            await update.message.reply_photo(photo=img)
    reply = ask_ai(uid, text)
    await update.message.reply_text(reply)

# ============ MAIN ============
if __name__ == "__main__":
    print("[BOOT] Starting Jeanny bot...", flush=True)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("pic", pic))
    app.add_handler(CommandHandler("picat", picat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    job_queue = app.job_queue
    job_queue.run_daily(good_morning, time=dt_time(hour=1, minute=0))
    job_queue.run_daily(good_night, time=dt_time(hour=14, minute=0))
    job_queue.run_daily(jealousy_check, time=dt_time(hour=5, minute=0))
    job_queue.run_daily(jealousy_check, time=dt_time(hour=9, minute=0))

    print("[BOOT] Starting webhook...", flush=True)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{os.environ.get('RENDER_EXTERNAL_URL')}/{TELEGRAM_TOKEN}",
    )
