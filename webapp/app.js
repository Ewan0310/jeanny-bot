// ===== JEANNY COMPANION MINI APP =====

const API_URL = 'https://jeanny-bot.onrender.com';

// DOM Elements
const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const character = document.getElementById('character');
const mouth = document.getElementById('mouth');
const bubbleText = document.getElementById('bubble-text');
const speechBubble = document.getElementById('speech-bubble');
const moodEmoji = document.getElementById('mood-emoji');
const moodText = document.getElementById('mood-text');
const blushLeft = document.getElementById('blush-left');
const blushRight = document.getElementById('blush-right');

// State
let isTyping = false;
let chatHistory = [];

// Init Telegram WebApp
if (window.Telegram && window.Telegram.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
}

// ===== MOOD SYSTEM =====
const moods = {
    happy:    { emoji: '😊', text: 'Happy', mouth: 'happy', blush: false },
    excited:  { emoji: '😆', text: 'Excited', mouth: 'happy', blush: false },
    loving:   { emoji: '😍', text: 'Loving', mouth: 'happy', blush: true },
    rindu:    { emoji: '🥺', text: 'Rindu', mouth: 'normal', blush: true },
    merajuk:  { emoji: '😤', text: 'Merajuk', mouth: 'normal', blush: false },
    sad:      { emoji: '😢', text: 'Sedih', mouth: 'normal', blush: false },
    playful:  { emoji: '😜', text: 'Playful', mouth: 'happy', blush: false },
    sleepy:   { emoji: '😴', text: 'Mengantuk', mouth: 'normal', blush: false },
    flirty:   { emoji: '😘', text: 'Flirty', mouth: 'happy', blush: true },
    shy:      { emoji: '😳', text: 'Malu', mouth: 'normal', blush: true }
};

function setMood(moodName) {
    const mood = moods[moodName] || moods.happy;
    moodEmoji.textContent = mood.emoji;
    moodText.textContent = mood.text;

    // Mouth
    mouth.className = '';
    if (mood.mouth === 'happy') mouth.classList.add('happy');

    // Blush
    if (mood.blush) {
        blushLeft.classList.add('visible');
        blushRight.classList.add('visible');
    } else {
        blushLeft.classList.remove('visible');
        blushRight.classList.remove('visible');
    }
}

// ===== CHARACTER ANIMATIONS =====
function characterTalk() {
    mouth.classList.add('talking');
    character.classList.add('character-talking');
}

function characterStopTalk() {
    mouth.classList.remove('talking');
    character.classList.remove('character-talking');
}

function characterReaction(type) {
    character.classList.remove('character-happy', 'character-shy');
    void character.offsetWidth; // trigger reflow
    if (type === 'happy') {
        character.classList.add('character-happy');
        setMood('happy');
    } else if (type === 'shy') {
        character.classList.add('character-shy');
        setMood('shy');
    } else if (type === 'flirty') {
        character.classList.add('character-shy');
        setMood('flirty');
    }
    setTimeout(() => {
        character.classList.remove('character-happy', 'character-shy');
    }, 1000);
}

function showSpeechBubble(text) {
    bubbleText.textContent = text.length > 80 ? text.substring(0, 80) + '...' : text;
    speechBubble.classList.remove('hidden');
    setTimeout(() => {
        speechBubble.classList.add('hidden');
    }, 4000);
}

// ===== CHAT FUNCTIONS =====
function addMessage(text, type) {
    const msg = document.createElement('div');
    msg.className = `message ${type}`;
    msg.textContent = text;
    messagesDiv.appendChild(msg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addTypingIndicator() {
    const msg = document.createElement('div');
    msg.className = 'message typing';
    msg.id = 'typing-indicator';
    msg.textContent = '💕 Jeanny sedang taip...';
    messagesDiv.appendChild(msg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}

// Detect mood from response
function detectMoodFromResponse(text) {
    const lower = text.toLowerCase();
    if (lower.includes('😘') || lower.includes('cinta') || lower.includes('sayang') || lower.includes('rindu')) return 'loving';
    if (lower.includes('haha') || lower.includes('😂') || lower.includes('lol') || lower.includes('gelak')) return 'excited';
    if (lower.includes('😢') || lower.includes('sedih') || lower.includes('😭')) return 'sad';
    if (lower.includes('😤') || lower.includes('merajuk') || lower.includes('hmm')) return 'merajuk';
    if (lower.includes('malu') || lower.includes('😳') || lower.includes('hehe')) return 'shy';
    if (lower.includes('😏') || lower.includes('nakal') || lower.includes('baby')) return 'flirty';
    if (lower.includes('mengantuk') || lower.includes('zzz') || lower.includes('tidur')) return 'sleepy';
    return 'happy';
}

// ===== SEND MESSAGE =====
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isTyping) return;

    // Add user message
    addMessage(text, 'user');
    messageInput.value = '';
    isTyping = true;

    // Show typing
    addTypingIndicator();
    characterTalk();

    try {
        // Call AI backend
        const response = await fetch(`${API_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                chat_id: window.Telegram?.WebApp?.initDataUnsafe?.user?.id || 'webapp_user'
            })
        });

        const data = await response.json();
        removeTypingIndicator();
        characterStopTalk();

        if (data.reply) {
            // Detect mood
            const mood = detectMoodFromResponse(data.reply);
            setMood(mood);

            // Character reaction
            if (mood === 'loving' || mood === 'flirty') characterReaction('flirty');
            else if (mood === 'shy') characterReaction('shy');
            else if (mood === 'happy' || mood === 'excited') characterReaction('happy');

            // Show speech bubble
            showSpeechBubble(data.reply);

            // Add bot message
            addMessage(data.reply, 'bot');
        } else {
            addMessage('Ehh sorry, Jeanny penat kejap 🥺', 'bot');
        }
    } catch (err) {
        removeTypingIndicator();
        characterStopTalk();
        addMessage('Connection error la~ try again? 🥺', 'bot');
        console.error(err);
    }

    isTyping = false;
}

// ===== EVENT LISTENERS =====
sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// Eye tracking (follow cursor)
document.addEventListener('mousemove', (e) => {
    const pupils = document.querySelectorAll('.pupil');
    pupils.forEach(pupil => {
        const rect = pupil.parentElement.getBoundingClientRect();
        const eyeX = rect.left + rect.width / 2;
        const eyeY = rect.top + rect.height / 2;
        const angle = Math.atan2(e.clientY - eyeY, e.clientX - eyeX);
        const distance = 3;
        pupil.style.transform = `translate(${Math.cos(angle) * distance}px, ${Math.sin(angle) * distance}px)`;
    });
});

// ===== INIT =====
setMood('happy');
addMessage('Haii~ Jeanny rindu awak tau! 💕', 'bot');

// Greeting based on time
const hour = new Date().getHours();
if (hour < 12) showSpeechBubble('Good morning sayang~ ☀️');
else if (hour < 18) showSpeechBubble('Petang ni jom borak! 💕');
else showSpeechBubble('Malam ni teman Jeanny ye~ 🌙');
