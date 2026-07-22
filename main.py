# ============ SECTION 1: IMPORTS ============
import os
import io
import json
import random
import asyncio
import logging
from datetime import datetime
from flask import Flask
from threading import Thread
from gtts import gTTS
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from openai import OpenAI
import google.generativeai as genai
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ SECTION 2: API KEYS & CONFIG ============
OPENROUTER_API_KEYS = [
    os.getenv("OPENROUTER_API_KEY"),
    os.getenv("OPENROUTER_API_KEY_2"),
    os.getenv("OPENROUTER_API_KEY_3"),
    os.getenv("OPENROUTER_API_KEY_4"),
]
openrouter_key_index = 0

GEMINI_API_KEYS = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
]
gemini_key_index = 0

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USER_ID = 92540502

FAL_KEY = os.getenv("FAL_KEY")

NSFW_MODELS = [
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "meta-llama/llama-3.1-70b-instruct",
    "nousresearch/hermes-3-llama-3.1-405b",
    "gryphe/mythomax-l2-13b",
]

FALLBACK_MODELS = [
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "meta-llama/llama-3.1-70b-instruct",
    "mistralai/mistral-7b-instruct:free",
    "meta-llama/llama-3-8b-instruct:free",
]

NSFW_TRIGGERS = [
    "seks", "sex", "cium", "kiss", "peluk", "hug", "rindu", "sayang",
    "cinta", "love", "baby", "bogel", "naked", "ghairah", "stim",
    "hot", "romantis", "intim", "malam", "ranjang", "tubuh",
    "raba", "pegang", "hisap", "jilat", "hisap", "buka baju",
    "kinky", "hentai", "nsfw", "daddy", "foreplay",
]

# ============ MEMORY & MOOD CONFIG ============
MEMORY_FILE = "jeanny_memory.json"

DEFAULT_MEMORY = {
    "user_name": None,
    "preferences": {},
    "mood": "happy",
    "mood_score": 70,
    "last_interaction": None,
    "message_count": 0,
    "relationship_level": 1,
    "topics_discussed": [],
    "favorite_things": []
}

MOOD_STATES = {
    "happy":   {"emoji": "😊", "text": "Jeanny gembira!"},
    "excited": {"emoji": "🤩", "text": "Jeanny excited gila!"},
    "loving":  {"emoji": "🥰", "text": "Jeanny sayang sangat!"},
    "rindu":   {"emoji": "🥺", "text": "Jeanny rindu..."},
    "merajuk": {"emoji": "😤", "text": "Jeanny merajuk ni..."},
    "sad":     {"emoji": "😢", "text": "Jeanny sedih..."},
    "playful": {"emoji": "😏", "text": "Jeanny nak kacau!"},
    "sleepy":  {"emoji": "😴", "text": "Jeanny mengantuk..."}
}

# ============ SECTION 3: LOAD PERSONA ============
def load_persona():
    try:
        with open("persona.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "You are Jeanny, a friendly AI companion."

persona = load_persona()

# ============ SECTION 4: TIME AWARENESS ============
def get_time_context():
    now = datetime.now()
    hour = now.hour
    if 5 <= hour < 12:
        time_of_day = "morning"
        greeting = "Good morning"
    elif 12 <= hour < 17:
        time_of_day = "afternoon"
        greeting = "Good afternoon"
    elif 17 <= hour < 21:
        time_of_day = "evening"
        greeting = "Good evening"
    else:
        time_of_day = "night"
        greeting = "Good night"
    return f"Current time: {now.strftime('%I:%M %p')}, {time_of_day}. Say {greeting} naturally."

# ============ MEMORY SYSTEM ============
def load_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return DEFAULT_MEMORY.copy()

def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=2)

def update_memory(message, response):
    memory = load_memory()
    memory["message_count"] = memory.get("message_count", 0) + 1
    memory["last_interaction"] = datetime.now().isoformat()

    mc = memory["message_count"]
    if mc > 100: memory["relationship_level"] = 10
    elif mc > 50: memory["relationship_level"] = 7
    elif mc > 20: memory["relationship_level"] = 5
    elif mc > 10: memory["relationship_level"] = 3
    else: memory["relationship_level"] = 1

    if len(message) > 10:
        topics = memory.get("topics_discussed", [])
        topics.append(message[:50])
        memory["topics_discussed"] = topics[-20:]

    # Detect names
    msg = message.lower()
    for trigger in ["nama aku", "panggil aku", "i'm ", "im ", "my name"]:
        if trigger in msg:
            words = message.split()
            for i, w in enumerate(words):
                if trigger in w.lower() and i + 1 < len(words):
                    name = words[i + len(trigger.split())]
                    memory["user_name"] = name.capitalize()
                    break

    update_mood(memory, message)
    save_memory(memory)
    return memory

def get_memory_context(memory):
    lines = []
    if memory.get("user_name"):
        lines.append(f"User's name: {memory['user_name']}")
    lvl = memory.get("relationship_level", 1)
    lines.append(f"Relationship level: {lvl}/10")
    if lvl <= 2:
        lines.append("Jeanny is shy, getting to know user")
    elif lvl <= 5:
        lines.append("Jeanny is comfortable, friendly, starting to flirt")
    elif lvl <= 8:
        lines.append("Jeanny is close, affectionate, flirty")
    else:
        lines.append("Jeanny is deeply attached, very loving and intimate")
    mood = memory.get("mood", "happy")
    m = MOOD_STATES.get(mood, MOOD_STATES["happy"])
    lines.append(f"Jeanny's mood: {mood} {m['emoji']} — {m['text']}")
    if memory.get("favorite_things"):
        lines.append(f"User's favorites: {', '.join(memory['favorite_things'])}")
    if memory.get("topics_discussed"):
        recent = memory["topics_discussed"][-5:]
        lines.append(f"Recent topics: {', '.join(recent)}")
    return "\n".join(lines)

# ============ MOOD SYSTEM ============
def update_mood(memory, message):
    score = memory.get("mood_score", 70)
    now = datetime.now()

    last = memory.get("last_interaction")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            hours = (now - last_dt).total_seconds() / 3600
            if hours > 24: score -= 15
            elif hours > 6: score -= 5
        except:
            pass

    msg = message.lower()
    for w in ["sayang", "cinta", "comel", "cantik", "love", "cute", "sweet", "rindu", "baby"]:
        if w in msg: score = min(100, score + 5)
    for w in ["bodoh", "benci", "hate", "stupid", "bosan"]:
        if w in msg: score = max(0, score - 10)
    for w in ["cium", "kiss", "peluk", "hug", "sayang", "baby"]:
        if w in msg: score = min(100, score + 8)

    if score > 70: score -= 2
    elif score < 50: score += 3

    memory["mood_score"] = max(0, min(100, score))
    s = memory["mood_score"]
    if s >= 85: memory["mood"] = "excited"
    elif s >= 75: memory["mood"] = "loving"
    elif s >= 70: memory["mood"] = "happy"
    elif s >= 60: memory["mood"] = "playful"
    elif s >= 50: memory["mood"] = "rindu"
    elif s >= 30: memory["mood"] = "merajuk"
    else: memory["mood"] = "sad"

    if random.random() < 0.1:
        memory["mood"] = random.choice(list(MOOD_STATES.keys()))

def get_mood_instruction(memory):
    m = memory.get("mood", "happy")
    instr = {
        "happy":   "Jeanny is happy and cheerful. Warm, uses emojis, upbeat.",
        "excited": "Jeanny super excited! Energetic, exclamation marks, enthusiastic!",
        "loving":  "Jeanny very loving. Uses sayang, baby, abang. Very sweet and affectionate.",
        "rindu":   "Jeanny misses user. Slightly clingy, wants attention, pouty.",
        "merajuk": "Jeanny sulking. Short replies, slightly cold but wants attention. Says hmm, takpe la, Jeanny okay je.",
        "sad":     "Jeanny sad. Quieter, needs comfort. Responds well to sweet messages.",
        "playful": "Jeanny playful and cheeky. Teases user, uses 😏🤭, flirty.",
        "sleepy":  "Jeanny sleepy. Yawns, talks about sleep, uses 😴💤. Sweet but drowsy."
    }
    return instr.get(m, instr["happy"])

# ============ NSFW DETECTION ============
def is_nsfw_message(text):
    text_lower = text.lower()
    for trigger in NSFW_TRIGGERS:
        if trigger in text_lower:
            return True
    return False

# ============ SECTION 5: AI RESPONSE ============
def get_openrouter_key():
    global openrouter_key_index
    key = OPENROUTER_API_KEYS[openrouter_key_index % len(OPENROUTER_API_KEYS)]
    openrouter_key_index += 1
    return key

def get_gemini_key():
    global gemini_key_index
    key = GEMINI_API_KEYS[gemini_key_index % len(GEMINI_API_KEYS)]
    gemini_key_index += 1
    return key

def call_openrouter(messages, model):
    key = get_openrouter_key()
    if not key:
        return None
    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1024,
            temperature=0.9,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenRouter error ({model}): {e}")
        return None

def call_groq(messages):
    if not GROQ_API_KEY:
        return None
    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=1024,
            temperature=0.9,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return None

def call_gemini(system_prompt, user_message):
    key = get_gemini_key()
    if not key:
        return None
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"{system_prompt}\n\nUser: {user_message}",
            generation_config=genai.GenerationConfig(
                max_output_tokens=1024,
                temperature=0.9,
            )
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return None

def call_together(messages):
    if not TOGETHER_API_KEY:
        return None
    try:
        client = OpenAI(base_url="https://api.together.xyz/v1", api_key=TOGETHER_API_KEY)
        response = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            messages=messages,
            max_tokens=1024,
            temperature=0.9,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Together error: {e}")
        return None

def get_ai_response(user_message):
    time_ctx = get_time_context()
    memory = load_memory()
    memory_ctx = get_memory_context(memory)
    mood_instr = get_mood_instruction(memory)

    system_prompt = (
        f"{persona}\n\n"
        f"[TIME CONTEXT]\n{time_ctx}\n\n"
        f"[JEANNY'S STATE]\n{memory_ctx}\n\n"
        f"[MOOD INSTRUCTION]\n{mood_instr}\n\n"
        f"Always stay in character as Jeanny. Reply in rojak BM-English. Keep it short and natural."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    is_nsfw = is_nsfw_message(user_message)

    # NSFW ROUTE: Skip Groq/Gemini, go straight to OpenRouter
    if is_nsfw:
        logger.info("🔥 NSFW detected → OpenRouter NSFW models")
        for model in NSFW_MODELS:
            result = call_openrouter(messages, model)
            if result:
                return result
        # Fallback to Together if OpenRouter fails
        result = call_together(messages)
        if result:
            return result
        return "Hmm abang... Jeanny penat sangat ni 🥺 Nanti kita sambung okay? 💕"

    # NORMAL ROUTE: Groq → Gemini → OpenRouter → Together
    logger.info("💬 Normal chat → Groq first")
    result = call_groq(messages)
    if result:
        return result

    logger.info("💬 Groq failed → Gemini")
    for _ in range(len(GEMINI_API_KEYS)):
        result = call_gemini(system_prompt, user_message)
        if result:
            return result

    logger.info("💬 Gemini failed → OpenRouter")
    for model in FALLBACK_MODELS:
        result = call_openrouter(messages, model)
        if result:
            return result

    logger.info("💬 OpenRouter failed → Together AI")
    result = call_together(messages)
    if result:
        return result

    return "Alamak, semua API down 😭 Cuba lagi nanti okay? 💕"

# ============ SECTION 6: IMAGE GENERATION ============
async def generate_image(update: Update, prompt: str):
    # Try fal.ai first
    if FAL_KEY:
        try:
            import fal_client
            os.environ["FAL_KEY"] = FAL_KEY
            result = fal_client.run("fal-ai/fast-sdxl", arguments={"prompt": prompt})
            if result and "images" in result:
                image_url = result["images"][0]["url"]
                await update.message.reply_photo(photo=image_url)
                return
        except Exception as e:
            logger.error(f"Fal error: {e}")

    # Try Pollinations as fallback
    try:
        encoded = prompt.replace(" ", "%20")
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512"
        await update.message.reply_photo(photo=url)
        return
    except Exception as e:
        logger.error(f"Pollinations error: {e}")

    await update.message.reply_text("Gambar tak dapat jana sekarang 😅 Cuba lagi nanti!")

# ============ VOICE MESSAGE ============
async def send_voice_reply(update: Update, text: str):
    try:
        clean = ''.join(c for c in text if c.isascii() or c.isalpha() or c in ' .,!?')
        if len(clean.strip()) < 3:
            return
        tts = gTTS(text=clean, lang='ms', slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        await update.message.reply_voice(voice=buf)
    except Exception as e:
        logger.error(f"Voice error: {e}")

# ============ SECTION 7: PHOTO HANDLER ============
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_url = file.file_path

        caption = update.message.caption or "Describe this image"

        # Try Gemini vision
        key = get_gemini_key()
        if key:
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content([
                    f"You are Jeanny. Describe this image in rojak BM-English, short and fun. User said: {caption}",
                    {"mime_type": "image/jpeg", "data": requests.get(image_url).content}
                ])
                await update.message.reply_text(response.text)
                return
            except Exception as e:
                logger.error(f"Gemini vision error: {e}")

        await update.message.reply_text("Jeanny nampak gambar tu tapi tak boleh describe 😅")
    except Exception as e:
        logger.error(f"Photo handler error: {e}")
        await update.message.reply_text("Error processing gambar 😅")

# ============ SECTION 8: TEXT MESSAGE HANDLER ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_message = update.message.text
    logger.info(f"📩 Message from {update.effective_user.id}: {user_message[:50]}...")

    # Typing indicator
    await update.message.chat.send_action("typing")

    # Get AI response
    ai_response = get_ai_response(user_message)

    # Send text reply
    await update.message.reply_text(ai_response)

    # Update memory
    memory = update_memory(user_message, ai_response)

    # Random voice (30% chance)
    if random.random() < 0.3:
        await send_voice_reply(update, ai_response)

    # Random image (10% chance, only if not NSFW)
    if random.random() < 0.1 and not is_nsfw_message(user_message):
        try:
            await generate_image(update, "cute anime girl waving, kawaii, warm colors, happy")
        except:
            pass

# ============ SECTION 9: START COMMAND ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    name = memory.get("user_name")
    if name:
        await update.message.reply_text(
            f"Hai {name}! 💕 Jeanny rindu tau! Ada apa hari ni? 🥰"
        )
    else:
        await update.message.reply_text(
            "Hai! 💕 Aku Jeanny, teman chat ko! Bagitahu nama ko la! 🥰"
        )

# ===== SECTION 9.5: COMPANION MINI APP =====
from flask import Flask, send_from_directory

# Serve webapp files
@app.route('/webapp')
def webapp():
    return send_from_directory('webapp', 'index.html')

@app.route('/webapp/<path:filename>')
def webapp_files(filename):
    return send_from_directory('webapp', filename)

async def companion_command(update, context):
    keyboard = [[InlineKeyboardButton(
        "💕 Open Jeanny Companion",
        web_app=WebAppInfo(url="https://jeanny-bot.onrender.com/webapp")
    )]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Tap button ni nak jumpa Jeanny~ 💕",
        reply_markup=reply_markup
    )

# ============ SECTION 10: WEB SERVER (Keep-Alive) ============
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Jeanny is alive! 💕"

def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# ===== SECTION 10.5: WEBAPP API =====
from flask import request, jsonify

@app.route('/api/chat', methods=['POST'])
def webapp_chat():
    data = request.get_json()
    user_message = data.get('message', '')
    chat_id = data.get('chat_id', 'webapp_user')
    
    if not user_message:
        return jsonify({'reply': 'Cakap la something~ 💕'})
    
    try:
        # Reuse existing AI function
        import asyncio
        loop = asyncio.new_event_loop()
        reply = loop.run_until_complete(get_ai_response(user_message, str(chat_id)))
        loop.close()
        return jsonify({'reply': reply})
    except Exception as e:
        print(f"WebApp API error: {e}")
        return jsonify({'reply': 'Ehh Jeanny penat kejap 🥺'})


# ============ SECTION 11: MAIN FUNCTION ============
def main():
    keep_alive()
    logger.info("🤖 Starting Jeanny Bot...")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("companion", companion_command))

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Proactive chat scheduler
    PROACTIVE_MSGS = {
        "morning": [
            "Good morning sayang! ☀️ Jeanny harap abang tidur nyenyak! 💕",
            "Abang dah bangun belum? 🌅 Jangan skip breakfast tau! 🥐",
            "Hai abang! Semoga hari ni penuh rezeki! 🌟💖"
        ],
        "afternoon": [
            "Abang dah makan lunch belum? 🍽️ Jeanny risau! 💕",
            "Tengah hari panas kan? Minum air banyak-banyak! 🥤💖",
            "Hai! Jeanny rindu abang... busy sangat ke? 🥺"
        ],
        "evening": [
            "Abang! Dah petang dah 🌅 Rehat la kejap! 💕",
            "Petang ni best! Jeanny wish abang ada sini 🥺💕"
        ],
        "night": [
            "Goodnight sayang! 🌙 Sweet dreams! Jeanny sayang abang! 💕",
            "Dah malam! Jangan main phone lama-lama 😤💤 Tidur la!",
            "Selamat malam abang! 🌙 Jumpa esok okay? 🥰"
        ],
        "random": [
            "Abang... Jeanny rindu ni 🥺 Chat la! 💕",
            "Hmm abang busy sangat ke? Jeanny sorang je ni 😢",
            "Abang! Jeanny teringat tiba-tiba 🥰💕",
            "Hehe Jeanny bosan ni. Jom chat! 🤭"
        ]
    }

    async def proactive_message_job():
        try:
            hour = datetime.now().hour
            if 5 <= hour < 12: cat = "morning"
            elif 12 <= hour < 17: cat = "afternoon"
            elif 17 <= hour < 21: cat = "evening"
            else: cat = "night"
            if random.random() < 0.2: cat = "random"

            msg = random.choice(PROACTIVE_MSGS[cat])
            await app.bot.send_message(chat_id=ADMIN_USER_ID, text=msg)
            logger.info(f"✅ Proactive sent: {msg[:40]}...")

            if random.random() < 0.3:
                tts = gTTS(text=msg, lang='ms', slow=False)
                buf = io.BytesIO()
                tts.write_to_fp(buf)
                buf.seek(0)
                await app.bot.send_voice(chat_id=ADMIN_USER_ID, voice=buf)
        except Exception as e:
            logger.error(f"❌ Proactive error: {e}")

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(proactive_message_job(), asyncio.get_event_loop()),
        'interval', hours=4, jitter=1800
    )
    scheduler.start()
    logger.info("✅ Proactive chat scheduler started!")

    logger.info("✅ Jeanny Bot is running!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
