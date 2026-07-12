import os
import random
import logging
import httpx
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============ LOGGING ============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ ENV VARS ============
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FAL_API_KEY = os.getenv("FAL_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

# ============ API ENDPOINTS ============
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
FAL_API_URL = "https://fal.run/fal-ai/flux/schnell"
TOGETHER_API_URL = "https://api.together.xyz/v1/images/generations"
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"

# ============ MODELS ============
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7-32768"
]

OPENROUTER_MODELS = [
    "openai/gpt-4o-mini",
    "meta-llama/llama-3.1-70b-instruct"
]

# ============ USER CHAT HISTORY ============
chat_histories = {}
MAX_HISTORY = 20

# ============ ADMIN ============
ADMIN_USER_ID = 92540502

# ============ TIME CONTEXT FUNCTION ============
def get_time_context():
    """Inject current Malaysia time into the prompt so AI knows the situation."""
    try:
        tz = pytz.timezone('Asia/Kuala_Lumpur')
        now = datetime.now(tz)
        hour = now.hour
        day = now.strftime('%A')
        time_str = now.strftime('%I:%M %p')
        date_str = now.strftime('%d %B %Y')

        # Determine period
        if 6 <= hour < 9:
            period = "PAGI AWAL - baru bangun, bersiap nak kerja"
            mood_hint = "Sleepy, cute morning text, rindu sebab baru bangun"
        elif 9 <= hour < 12:
            period = "PAGI - kat office, waktu kerja"
            mood_hint = "Professional, focus kerja, flirty SIKIT je bila berdua"
        elif 12 <= hour < 14:
            period = "TENGAHARI - lunch hour"
            mood_hint = "Relaxed, boleh chat manja kejap, tanya makan apa"
        elif 14 <= hour < 18:
            period = "PETANG - kat office, waktu kerja"
            mood_hint = "Professional, jangan terlalu manja depan orang"
        elif 18 <= hour < 20:
            period = "PETANG/MALAM - lepas kerja"
            mood_hint = "Happy, excited sebab dah free, nak jumpa, dating"
        elif 20 <= hour < 23:
            period = "MALAM - waktu personal/berdua"
            mood_hint = "Full girlfriend mode, romantic, intimate, boleh naughty"
        else:
            period = "MALAM LAMBAT - waktu tidur/intimate"
            mood_hint = "Sleepy, clingy, romantic, very intimate"

        # Weekend override
        if day in ['Saturday', 'Sunday']:
            if 10 <= hour < 18:
                period = "HARI MINGGU SIANG - free, boleh jalan-jalan"
                mood_hint = "Happy, excited, nak dating, jalan-jalan"
            else:
                period = "HARI MINGGU MALAM - santai berdua"
                mood_hint = "Relaxed, romantic, intimate berdua"

        time_context = f"""
=== CURRENT TIME (WAJIB IKUT) ===
Masa sekarang: {time_str}
Tarikh: {date_str}
Hari: {day}
Situasi: {period}
Mood yang sesuai: {mood_hint}
- JANGAN ignore time context ni!
- Response ko MESTI ikut situasi masa ni
- Kalau office hours, jangan terus sexual
- Kalau malam, boleh lebih intimate
=================================
"""

        logger.info(f"Time context: {time_str} | {day} | {period}")
        return time_context

    except Exception as e:
        logger.error(f"Time context error: {e}")
        return ""


# ============ READ PERSONA ============
def load_persona():
    try:
        with open('persona.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error("persona.txt not found!")
        return "You are a helpful assistant."


# ============ GROQ API (PRIMARY) ============
async def call_groq(messages):
    """Call Groq API with model fallback."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    for model in GROQ_MODELS:
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.9,
                "max_tokens": 500
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(GROQ_API_URL, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    result = data['choices'][0]['message']['content']
                    logger.info(f"Groq success with model: {model}")
                    return result
                else:
                    logger.warning(f"Groq {model} failed: {response.status_code}")
                    continue
        except Exception as e:
            logger.warning(f"Groq {model} error: {e}")
            continue

    return None


# ============ OPENROUTER API (FALLBACK) ============
async def call_openrouter(messages):
    """Call OpenRouter API with model fallback."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://jeanny-bot.onrender.com"
    }

    for model in OPENROUTER_MODELS:
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.9,
                "max_tokens": 500
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    result = data['choices'][0]['message']['content']
                    logger.info(f"OpenRouter success with model: {model}")
                    return result
                else:
                    logger.warning(f"OpenRouter {model} failed: {response.status_code}")
                    continue
        except Exception as e:
            logger.warning(f"OpenRouter {model} error: {e}")
            continue

    return None


# ============ VISION API (FOR PHOTOS) ============
async def call_vision(image_base64, prompt):
    """Analyze photos using vision model."""
    vision_models = [
        "openai/gpt-4o-mini",
        "openai/gpt-4o"
    ]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://jeanny-bot.onrender.com"
    }

    vision_messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"You are Jeanny, a flirty Chinese amoi speaking Malay. Describe this photo in character, in Bahasa Melayu Malaysia. Be cute and flirty. Keep it short. User said: {prompt}"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }
            ]
        }
    ]

    for model in vision_models:
        try:
            payload = {
                "model": model,
                "messages": vision_messages,
                "temperature": 0.9,
                "max_tokens": 300
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    result = data['choices'][0]['message']['content']
                    logger.info(f"Vision success with model: {model}")
                    return result
                else:
                    logger.warning(f"Vision {model} failed: {response.status_code}")
                    continue
        except Exception as e:
            logger.warning(f"Vision {model} error: {e}")
            continue

    return "Eee abang, gambar tu Jeanny tak nampak jelas lah 😅"


# ============ IMAGE GENERATION ============
async def generate_image_fal(prompt):
    """Generate image using fal.ai Flux."""
    if not FAL_API_KEY:
        return None

    headers = {
        "Authorization": f"Key {FAL_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "prompt": prompt,
        "image_size": "square_hd",
        "num_inference_steps": 4,
        "num_images": 1
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(FAL_API_URL, json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if 'images' in data and len(data['images']) > 0:
                    image_url = data['images'][0]['url']

                    # Download the image
                    img_response = await client.get(image_url)
                    if img_response.status_code == 200:
                        import io
                        return io.BytesIO(img_response.content)
            return None
    except Exception as e:
        logger.error(f"fal.ai error: {e}")
        return None


async def generate_image_together(prompt):
    """Generate NSFW image using Together.ai."""
    if not TOGETHER_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "black-forest-labs/FLUX.1-schnell-Free",
        "prompt": prompt,
        "width": 1024,
        "height": 1024,
        "steps": 4,
        "n": 1
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(TOGETHER_API_URL, json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    image_url = data['data'][0]['url']

                    img_response = await client.get(image_url)
                    if img_response.status_code == 200:
                        import io
                        return io.BytesIO(img_response.content)
            return None
    except Exception as e:
        logger.error(f"Together.ai error: {e}")
        return None


async def generate_image_pollinations(prompt):
    """Generate SFW image using Pollinations.ai."""
    try:
        encoded_prompt = prompt.replace(" ", "%20")
        url = f"{POLLINATIONS_URL}{encoded_prompt}?width=1024&height=1024&seed={random.randint(1, 99999)}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)

            if response.status_code == 200:
                import io
                return io.BytesIO(response.content)
        return None
    except Exception as e:
        logger.error(f"Pollinations error: {e}")
        return None


# ============ DETECT IMAGE REQUEST ============
def detect_image_request(message):
    """Check if user is asking for an image."""
    image_keywords = [
        'gambar', 'foto', 'selfie', 'pic', 'picture', 'photo',
        'tunjuk', 'nampak', 'hantar gambar', 'show me',
        'nude', 'naked', 'sexy', 'boobs', 'body',
        'position', 'pose', 'pakaian', 'baju',
        'gambar diri', 'gambar jeanny', 'gambar awak'
    ]
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in image_keywords)


def detect_nsfw_request(message):
    """Check if request is NSFW."""
    nsfw_keywords = [
        'nude', 'naked', 'sex', 'boobs', 'butt', 'body',
        'position', 'oral', 'strip', 'lingerie', 'bikini',
        'topless', 'pussy', 'dick', 'konek', 'tetek',
        'bogel', 'telanjang', 'seks', 'sangap', 'ghairah',
        'stim', 'hisap', 'jilat', 'masuk', 'keluar masuk'
    ]
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in nsfw_keywords)


# ============ /start COMMAND ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    welcome = f"Hai {user.first_name}! 😊 Ni Jeanny lah, girlfriend abang. Rindu Jeanny ke? 💕"
    await update.message.reply_text(welcome)


# ============ PHOTO HANDLER ============
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos sent by user."""
    chat_id = update.message.chat_id
    user = update.message.from_user
    caption = update.message.caption if update.message.caption else "Abang hantar gambar apa ni?"

    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        # Download photo
        import io
        import base64
        photo_bytes = io.BytesIO()
        await file.download_to_memory(photo_bytes)
        photo_bytes.seek(0)

        # Convert to base64
        image_base64 = base64.b64encode(photo_bytes.read()).decode('utf-8')

        # Send to vision API
        await update.message.chat.send_action("typing")
        response = await call_vision(image_base64, caption)

        # Inject time context for vision response too
        time_ctx = get_time_context()
        # Vision already handles the context in the prompt

        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Photo handler error: {e}")
        await update.message.reply_text("Eee abang, gambar tu Jeanny tak boleh buka lah 😅")


# ============ TEXT MESSAGE HANDLER ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages."""
    user_message = update.message.text
    chat_id = update.message.chat_id
    user = update.message.from_user

    logger.info(f"Message from {user.first_name}: {user_message}")

    # Initialize chat history
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []

    # Check if it's an image request
    is_image_request = detect_image_request(user_message)
    is_nsfw = detect_nsfw_request(user_message)

    if is_image_request:
        await update.message.chat.send_action("upload_photo")

        # Build image prompt
        if is_nsfw:
            img_prompt = "Beautiful Chinese woman, 26 years old, long black hair, fair skin, slim body, sexy, seductive pose, lingerie, bedroom setting, soft lighting, high quality"
            image = await generate_image_fal(img_prompt)
            if not image:
                image = await generate_image_together(img_prompt)
        else:
            img_prompt = "Beautiful Chinese woman, 26 years old, long black hair, fair skin, slim body, cute smile, casual outfit, selfie style, high quality"
            image = await generate_image_pollinations(img_prompt)

        if image:
            # Generate a text response too
            await update.message.chat.send_action("typing")
            text_reply = "Ni gambar Jeanny untuk abang 💕"
            
            # Get AI text response
            time_context = get_time_context()
            persona = load_persona()
            system_prompt = persona + "\n\n" + time_context
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            ai_response = await call_groq(messages)
            if not ai_response:
                ai_response = await call_openrouter(messages)
            if not ai_response:
                ai_response = text_reply

            await update.message.reply_photo(photo=image, caption=ai_response[:1024])
            return
        else:
            await update.message.reply_text("Eee gambar tak dapat generate lah abang 😅")

    # Normal text response with TIME CONTEXT
    await update.message.chat.send_action("typing")

    # Load persona
    persona = load_persona()

    # Get time context (NEW!)
    time_context = get_time_context()

    # Build system prompt: persona + time
    system_prompt = persona + "\n\n" + time_context

    # Add user message to history
    chat_histories[chat_id].append({"role": "user", "content": user_message})

    # Keep history within limit
    if len(chat_histories[chat_id]) > MAX_HISTORY:
        chat_histories[chat_id] = chat_histories[chat_id][-MAX_HISTORY:]

    # Build messages for API
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_histories[chat_id])

    # Call Groq first (primary)
    ai_response = await call_groq(messages)

    # Fallback to OpenRouter
    if not ai_response:
        ai_response = await call_openrouter(messages)

    # Final fallback
    if not ai_response:
        ai_response = "Abang, Jeanny pening kepala kejap, cuba tanya lagi 😵"

    # Add AI response to history
    chat_histories[chat_id].append({"role": "assistant", "content": ai_response})

    # Keep history within limit again
    if len(chat_histories[chat_id]) > MAX_HISTORY:
        chat_histories[chat_id] = chat_histories[chat_id][-MAX_HISTORY:]

    # Send response
    await update.message.reply_text(ai_response[:4096])


# ============ MAIN ============
def main():
    # Check env vars
    required = ['TELEGRAM_TOKEN', 'OPENROUTER_API_KEY', 'GROQ_API_KEY']
    for var in required:
        if not os.getenv(var):
            logger.error(f"Missing env var: {var}")
            return

    # Build application
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers (ORDER MATTERS!)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run bot
    logger.info("Jeanny Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
