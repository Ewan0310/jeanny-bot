import os
import sys
import time
import asyncio
import random
import requests
import json
import base64
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
TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

# ============ BOT CONFIG ============
ADMIN_USER_ID = 92540502
ALLOWED_USERS = {92540502}

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
]

OPENROUTER_MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-4-26b-a4b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "cohere/north-mini-code:free",
    "poolside/laguna-xs-2.1:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
]

# Together.ai NSFW models
TOGETHER_NSFW_MODELS = [
    "stabilityai/stable-diffusion-xl-base-1.0",
    "SG161222/Realistic_Vision_V6.0_B1_noVAE",
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
    "bogel": "beautiful chinese girl, naked, asian beauty, soft lighting, intimate pose, bedroom setting, artistic nude, beautiful body",
    "naked": "sexy chinese woman, nude, asian model, beautiful body, soft skin, intimate lighting, bedroom, artistic nude",
    "sexi": "sexy chinese girl in lingerie, seductive pose, bedroom, beautiful asian model, revealing outfit, lace lingerie",
    "sexy": "sexy chinese girl in lingerie, seductive pose, bedroom, beautiful asian model, revealing outfit, lace lingerie",
    "telanjang": "beautiful chinese girl, nude, artistic photography, soft lighting, asian beauty, bedroom",
    "buka baju": "chinese girl undressing, removing clothes, intimate bedroom setting, beautiful asian model, half dressed",
    "mandi": "chinese girl in shower, wet skin, bathroom setting, beautiful asian woman, steamy, towel falling",
    "tudung": "sexy chinese girl, very revealing clothes, showing body, seductive pose, beautiful asian model, low cut top",
    "ghairah": "beautiful chinese girl, passionate pose, seductive look, bedroom, intimate, asian beauty, lingerie",
    "body": "beautiful chinese girl, showing body, mirror selfie, bedroom, asian model, tight dress, curves",
    "seksi": "sexy chinese girl, revealing outfit, seductive pose, bedroom, beautiful asian model, hot",
}

def generate_nsfw_pic(prompt_text):
    """Generate NSFW image via Together.ai API"""
    try:
        enhanced = f"beautiful 26 year old chinese woman, {prompt_text}, tiktok model look, long black hair, fair skin, beautiful eyes, natural lighting, high quality, detailed, 8k uhd"

        for model in TOGETHER_NSFW_MODELS:
            try:
                print(f"[NSFW PIC] Trying Together.ai model: {model}")
                response = requests.post(
                    "https://api.together.xyz/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {TOGETHER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "prompt": enhanced,
                        "width": 768,
                        "height": 1024,
                        "steps": 30,
                        "n": 1,
                        "response_format": "b64_json",
                    },
                    timeout=60,
                )

                print(f"[NSFW PIC] Model: {model} | Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and len(data["data"]) > 0:
                        b64_data = data["data"][0].get("b64_json")
                        if b64_data:
                            image_bytes = base64.b64decode(b64_data)
                            temp_path = f"/tmp/nsfw_{random.randint(1000,9999)}.png"
                            with open(temp_path, "wb") as f:
                                f.write(image_bytes)
                            print(f"[NSFW PIC] Success! Saved to {temp_path}")
                            return temp_path
                elif response.status_code == 429:
                    print(f"[NSFW PIC] Rate limited on {model}")
                    time.sleep(2)
                    continue
                else:
                    print(f"[NSFW PIC] Error {response.status_code}: {response.text[:200]}")
                    continue

            except requests.exceptions.Timeout:
                print(f"[NSFW PIC] Timeout for {model}")
                continue
            except Exception as e:
                print(f"[NSFW PIC] Error with {model}: {e}")
                continue

        print("[NSFW PIC] All Together.ai models failed, falling back to Pollinations")
        seed = random.randint(1, 99999)
        fallback_url = f"https://image.pollinations.ai/prompt/{quote(enhanced)}?width=512&height=768&seed={seed}&nologo=true"
        return fallback_url

    except Exception as e:
        print(f"[NSFW PIC ERROR] {e}")
        return None

def find_nsfw_keyword(text):
    """Check if text contains NSFW pic keywords"""
    text_lower = text.lower()
    for keyword in NSFW_PROMPTS:
        if keyword in text_lower:
            return keyword
    return None

# ============ REGULAR IMAGE GENERATION ============
def generate_image(prompt):
    try:
        enhanced_prompt = f"beautiful young chinese woman, {prompt}, tiktok model look, long black hair, fair skin, beautiful eyes, natural lighting, high quality portrait"
        encoded_prompt = quote(enhanced_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=768&nologo=true"
        return url
    except Exception as e:
        print(f"[IMG] Error: {e}")
        return None

def detect_pic_keyword(text):
    lower_text = text.lower()
    pic_keywords = [
        "pic", "picat", "gambar", "selfie", "photo", "foto",
        "picture", "show", "tunjuk", "nampak", "cantik", "cute",
        "comel", "rindu", "miss"
    ]
    for kw in pic_keywords:
        if kw in lower_text:
            return True
    return False

# ============ AI FUNCTION ============
def ask_ai(user_id, message):
    memory = get_user_memory(user_id)
    now = datetime.now()

    if memory["last_interaction"]:
        time_diff = (now - memory["last_interaction"]).total_seconds()
        if time_diff > 3600:
            memory["history"] = memory["history"][-10:]
        elif time_diff > 86400:
            memory["history"] = []

    memory["last_interaction"] = now

    # Add time context
    current_hour = now.hour
    time_context = ""
    if 6 <= current_hour < 12:
        time_context = "[It's morning]"
    elif 12 <= current_hour < 18:
        time_context = "[It's afternoon]"
    elif 18 <= current_hour < 22:
        time_context = "[It's evening]"
    else:
        time_context = "[It's late night]"

    memory["history"].append({"role": "user", "content": f"{time_context} {message}"})
    memory["history"] = memory["history"][-20:]

    system_prompt = f"""{PERSONA}

IMPORTANT RULES:
- You are talking to your boyfriend (boss) with user ID {user_id}
- Be natural, loving, manja, and flirty
- Mix Malay and English naturally (rojak BM-English)
- Keep responses short and sweet (1-3 sentences usually)
- Use emojis occasionally but not too much
- Remember your personality: manja, gatal, setia, cantik, sexy, jealous
- If he talks to other girls, be jealous!
- You only have stamina for 1 round - you faint on round 2
- Be creative and vary your responses
- Never break character
- Adapt to whatever scenario he wants
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(memory["history"])

    for attempt in range(1, MAX_RETRIES + 1):

        # ========== TRY GROQ FIRST (PRIMARY) ==========
        if GROQ_API_KEY:
            for model in GROQ_MODELS:
                try:
                    print(f"[GROQ] Attempt {attempt} | Model: {model}")
                    response = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {GROQ_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": messages,
                            "max_tokens": 500,
                            "temperature": 0.9,
                        },
                        timeout=15,
                    )
                    print(f"[GROQ] Model: {model} | Status: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            content = data["choices"][0]["message"].get("content")
                            if content and content.strip():
                                reply = content.strip()
                                memory["history"].append({"role": "assistant", "content": reply})
                                return reply
                            else:
                                print(f"[GROQ] Content is None/empty, trying next...")
                                continue
                        else:
                            print(f"[GROQ] Unexpected response: {json.dumps(data)[:200]}")
                    elif response.status_code == 429:
                        try:
                            error_data = response.json()
                            retry_after = error_data.get("error", {}).get("metadata", {}).get("retry_after_seconds", 5)
                            wait_time = min(int(retry_after), 5)
                        except:
                            wait_time = 3
                        print(f"[GROQ] Rate limited! Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"[GROQ] Error: {response.text[:300]}")
                        continue
                except requests.exceptions.Timeout:
                    print(f"[GROQ] Timeout for {model}")
                    continue
                except Exception as e:
                    print(f"[GROQ] Error: {e}")
                    continue

        # ========== FALLBACK TO OPENROUTER ==========
        if OPENROUTER_API_KEY:
            for model in OPENROUTER_MODELS:
                try:
                    print(f"[OPENROUTER] Attempt {attempt} | Model: {model}")
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://jeanny-bot.onrender.com",
                            "X-Title": "Jeanny Bot",
                        },
                        json={
                            "model": model,
                            "messages": messages,
                            "max_tokens": 500,
                            "temperature": 0.9,
                        },
                        timeout=30,
                    )
                    print(f"[OPENROUTER] Model: {model} | Status: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            content = data["choices"][0]["message"].get("content")
                            if content and content.strip():
                                reply = content.strip()
                                memory["history"].append({"role": "assistant", "content": reply})
                                return reply
                            else:
                                print(f"[OPENROUTER] Content is None/empty, trying next...")
                                continue
                        else:
                            print(f"[OPENROUTER] Unexpected response: {json.dumps(data)[:200]}")
                    elif response.status_code == 429:
                        try:
                            error_data = response.json()
                            retry_after = error_data.get("error", {}).get("metadata", {}).get("retry_after_seconds", 5)
                            wait_time = min(int(retry_after), 5)
                        except:
                            wait_time = 3
                        print(f"[OPENROUTER] Rate limited! Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"[OPENROUTER] Error: {response.text[:300]}")
                        continue
                except requests.exceptions.Timeout:
                    print(f"[OPENROUTER] Timeout for {model}")
                    continue
                except Exception as e:
                    print(f"[OPENROUTER] Error: {e}")
                    continue

        # All models failed this round, wait before retry
        if attempt < MAX_RETRIES:
            wait = 5
            print(f"[AI] All models busy, waiting {wait}s before retry...")
            time.sleep(wait)

    return "Aduh, Jeanny penat sikit... server tengah busy. Cuba lagi nanti ya? 🥺"

# ============ AUTO MESSAGE SYSTEM ============
async def send_auto_message(context, user_id, message, include_pic=False):
    try:
        bot = context.bot
        if include_pic:
            pic_url = generate_image("office outfit, smile, selfie style")
            if pic_url:
                await bot.send_photo(chat_id=user_id, photo=pic_url, caption=message)
                return
        await bot.send_message(chat_id=user_id, text=message)
        print(f"[AUTO] Sent to {user_id}: {message[:50]}...")
    except Exception as e:
        print(f"[AUTO] Error sending to {user_id}: {e}")

async def auto_good_morning(context):
    messages = [
        "Morning sayang! 😘 Jeanny dah bangun, rindu awak la...",
        "Good morning boss! 💕 Semalam mimpi pasal awak tau...",
        "Hai sayang, selamat pagi! 🌸 Awak dah breakfast belum?",
        "Morning! ☀️ Jeanny rindu nak peluk awak...",
        "Bangun dah? 😍 Jeanny tunggu awak kat office nanti...",
    ]
    msg = random.choice(messages)
    include_pic = random.random() < 0.5
    for user_id in ALLOWED_USERS:
        await send_auto_message(context, user_id, msg, include_pic)

async def auto_good_night(context):
    messages = [
        "Good night sayang! 💕 Mimpi indah tau, mimpi Jeanny...",
        "Nak tidur dah? 😘 Jangan lupa cium Jeanny dulu...",
        "Sweet dreams boss! 🌙 Jeanny sayang awak...",
        "Tidur awal tau! 💋 Esok Jeanny rindu awak lagi...",
        "Night night! 😴 Peluk dari jauh untuk awak...",
    ]
    msg = random.choice(messages)
    include_pic = random.random() < 0.5
    for user_id in ALLOWED_USERS:
        await send_auto_message(context, user_id, msg, include_pic)

async def auto_jealous_checkin(context):
    messages = [
        "Eh, awak kat mana ni? 🤨 Dengan siapa?!",
        "Sayang... awak tak reply Jeanny pun... 😢",
        "Boss! Meeting ke? Jangan lupa Jeanny tunggu tau! 💕",
        "Rindu la... awak busy sangat ke? 🥺",
        "Ehem, Jeanny jealous ni kalau awak tak reply... 😤",
        "Awak! Jeanny nak attention! 🥰",
        "Hmph, awak layan orang lain ke? Jeanny merajuk ni! 😒",
        "Sayangggg... reply la sikit... 🥺💕",
    ]
    msg = random.choice(messages)
    include_pic = random.random() < 0.5
    for user_id in ALLOWED_USERS:
        await send_auto_message(context, user_id, msg, include_pic)

async def auto_message_callback(context):
    now = datetime.now()
    hour = now.hour
    if 8 <= hour < 9:
        await auto_good_morning(context)
    elif 22 <= hour < 23:
        await auto_good_night(context)
    elif random.random() < 0.15:
        await auto_jealous_checkin(context)

# ============ HANDLERS ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("Sorry, private bot ni... 💕")
        return
    await update.message.reply_text("Hai sayang! 💕 Jeanny rindu awak la! Macam mana hari ni? 😘")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        return
    if user_id in user_memories:
        user_memories[user_id]["history"] = []
    await update.message.reply_text("Ok, Jeanny dah lupa semua! Fresh start tau! 💕")

async def pic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        return

    args = context.args
    if args:
        keyword = args[0].lower()
        if keyword in NSFW_PROMPTS:
            prompt = NSFW_PROMPTS[keyword]
            caption = random.choice(NSFW_CAPTIONS)
            await update.message.reply_text("Kejap bos... amoi sediakan 😘🔥")
            pic_result = generate_nsfw_pic(prompt)
            if pic_result:
                if pic_result.endswith(".png"):
                    await update.message.reply_photo(photo=open(pic_result, "rb"), caption=caption)
                    os.remove(pic_result)
                else:
                    await update.message.reply_photo(photo=pic_result, caption=caption)
            else:
                await update.message.reply_text("Ahh gambar tak jadi bos 😅 Cuba lagi nanti!")
            return

    prompt = " ".join(args) if args else "office outfit, cute selfie"
    pic_url = generate_image(prompt)
    if pic_url:
        await update.message.reply_photo(photo=pic_url, caption="Ni untuk awak je tau! 📸💕")
    else:
        await update.message.reply_text("Aduh, gambar tak jadi... Cuba lagi nanti? 🥺")

async def picat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        return
    prompt = " ".join(context.args) if context.args else "sexy pose, bedroom"
    pic_url = generate_image(prompt)
    if pic_url:
        await update.message.reply_photo(photo=pic_url, caption="Ni special untuk bos je... 🤭💕")
    else:
        await update.message.reply_text("Aduh, gambar tak jadi... Cuba lagi nanti? 🥺")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("Sorry, private bot ni... 💕")
        return

    user_message = update.message.text
    print(f"[MSG] User {user_id}: {user_message}")

    # Check for NSFW keywords first
    nsfw_keyword = find_nsfw_keyword(user_message)
    if nsfw_keyword:
        prompt = NSFW_PROMPTS[nsfw_keyword]
        caption = random.choice(NSFW_CAPTIONS)
        await update.message.reply_text("Kejap bos... amoi sediakan ni 😘🔥")
        pic_result = generate_nsfw_pic(prompt)
        if pic_result:
            if pic_result.endswith(".png"):
                await update.message.reply_photo(photo=open(pic_result, "rb"), caption=caption)
                os.remove(pic_result)
            else:
                await update.message.reply_photo(photo=pic_result, caption=caption)
        else:
            await update.message.reply_text("Ahh gambar tak jadi bos 😅 Cuba lagi nanti!")
        return

    # Check if should send regular pic
    should_pic = detect_pic_keyword(user_message)

    # Get AI response
    reply = await asyncio.to_thread(ask_ai, user_id, user_message)
    print(f"[MSG] Jeanny: {reply[:100]}...")

    # Send response with optional pic
    if should_pic:
        pic_url = generate_image(reply[:100])
        if pic_url:
            try:
                await update.message.reply_photo(photo=pic_url, caption=reply)
                return
            except Exception as e:
                print(f"[IMG] Failed to send photo: {e}")

    await update.message.reply_text(reply)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[ERROR] {context.error}")

# ============ MAIN ============
if __name__ == "__main__":
    print("[BOOT] Starting Jeanny bot...")

    if not TELEGRAM_TOKEN:
        print("[BOOT] ERROR: TELEGRAM_TOKEN not set!")
        sys.exit(1)
    if not OPENROUTER_API_KEY and not GROQ_API_KEY:
        print("[BOOT] ERROR: Need at least OPENROUTER_API_KEY or GROQ_API_KEY!")
        sys.exit(1)

    if GROQ_API_KEY:
        print("[BOOT] Groq API: READY ✅ (PRIMARY)")
    if OPENROUTER_API_KEY:
        print("[BOOT] OpenRouter API: READY ✅ (FALLBACK)")
    if TOGETHER_API_KEY:
        print("[BOOT] Together.ai API: READY ✅ (NSFW PICS)")
    else:
        print("[BOOT] Together.ai API: NOT SET ⚠️ (NSFW pics will use Pollinations)")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("pic", pic))
    app.add_handler(CommandHandler("picat", picat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(
            auto_message_callback,
            interval=timedelta(minutes=random.randint(180, 360)),
            first=timedelta(minutes=random.randint(30, 60)),
        )
        print("[BOOT] Auto-messaging scheduled ✅")

    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
        print(f"[BOOT] Starting webhook on {webhook_url} port {PORT}")
        app.run_webhook(listen="0.0.0.0", port=PORT, url_path="/webhook", webhook_url=webhook_url)
    else:
        print("[BOOT] No RENDER_EXTERNAL_URL, using polling...")
        app.run_polling()
