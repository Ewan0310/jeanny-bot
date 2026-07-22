// ===== JEANNY COMPANION APP =====

const API_URL = '/api/chat';
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const speechBubble = document.getElementById('speechBubble');
const bubbleText = document.getElementById('bubbleText');
const character = document.getElementById('character');
const face = document.getElementById('face');
const moodEmoji = document.getElementById('moodEmoji');
const heartsContainer = document.getElementById('heartsContainer');

// ===== INIT TELEGRAM WEBAPP =====
try {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
} catch (e) {
    console.log('Not in Telegram WebApp');
}

// ===== STATE =====
let isTalking = false;
let currentMood = 'happy';

// ===== VOICE SYSTEM =====
function speakText(text) {
    if (!('speechSynthesis' in window)) return;
    
    // Clean text - remove emojis
    let clean = text.replace(/[\u{1F600}-\u{1F9FF}]/gu, '').replace(/[\u{2600}-\u{26FF}]/gu, '').trim();
    if (clean.length < 3) return;
    
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(clean);
    
    // Try Malay/English voice
    const voices = window.speechSynthesis.getVoices();
    const malayVoice = voices.find(v => v.lang.startsWith('ms') || v.lang.startsWith('id'));
    const englishVoice = voices.find(v => v.lang.startsWith('en'));
    
    if (malayVoice) utter.voice = malayVoice;
    else if (englishVoice) utter.voice = englishVoice;
    
    utter.rate = 1.1;
    utter.pitch = 1.4; // Cute high pitch
    utter.volume = 0.8;
    
    window.speechSynthesis.speak(utter);
}

// Preload voices
window.speechSynthesis.onvoiceschanged = () => {
    window.speechSynthesis.getVoices();
};

// ===== MOOD MAPPING =====
const moodFaces = {
    happy:   { emoji: '😊', class: 'smile' },
    excited: { emoji: '🤩', class: 'happy' },
    loving:  { emoji: '🥰', class: 'blushing' },
    rindu:   { emoji: '🥺', class: '' },
    merajuk: { emoji: '😤', class: '' },
    sad:     { emoji: '😢', class: '' },
    playful: { emoji: '😏', class: 'blushing' },
    sleepy:  { emoji: '😴', class: '' }
};

// ===== DETECT MOOD FROM RESPONSE =====
function detectMood(text) {
    const t = text.toLowerCase();
    if (t.includes('sayang') || t.includes('baby') || t.includes('💕') || t.includes('🥰')) return 'loving';
    if (t.includes('rindu') || t.includes('🥺') || t.includes('miss')) return 'rindu';
    if (t.includes('hmm') || t.includes('takpe') || t.includes('😤')) return 'merajuk';
    if (t.includes('sedih') || t.includes('😢') || t.includes('sad')) return 'sad';
    if (t.includes('haha') || t.includes('🤭') || t.includes('😏') || t.includes('kacau')) return 'playful';
    if (t.includes('mengantuk') || t.includes('😴') || t.includes('penat')) return 'sleepy';
    if (t.includes('!') && t.includes('💕')) return 'excited';
    return 'happy';
}

// ===== SET MOOD =====
function setMood(mood) {
    currentMood = mood;
    const m = moodFaces[mood] || moodFaces.happy;
    moodEmoji.textContent = m.emoji;
    face.className = 'face';
    if (m.class) face.classList.add(m.class);
}

// ===== SHOW SPEECH BUBBLE =====
function showBubble(text, duration = 4000) {
    bubbleText.textContent = text;
    speechBubble.classList.add('show');
    face.classList.add('talking');
    isTalking = true;

    // Speak with voice!
    speakText(text);

    setTimeout(() => {
        speechBubble.classList.remove('show');
        face.classList.remove('talking');
        isTalking = false;
    }, duration);
}

// ===== SPAWN HEARTS =====
function spawnHearts(count = 5) {
    for (let i = 0; i < count; i++) {
        setTimeout(() => {
            const heart = document.createElement('div');
            heart.className = 'floating-heart';
            heart.textContent = ['💕', '💖', '💗', '💝', '❤️'][Math.floor(Math.random() * 5)];
            heart.style.left = (30 + Math.random() * 40) + '%';
            heart.style.bottom = '30%';
            heartsContainer.appendChild(heart);
            setTimeout(() => heart.remove(), 3000);
        }, i * 200);
    }
}

// ===== ADD CHAT MESSAGE =====
function addMessage(text, isUser = false) {
    const msg = document.createElement('div');
    msg.className = `msg ${isUser ? 'user' : 'bot'}`;
    msg.textContent = text;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ===== SEND MESSAGE =====
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;

    addMessage(text, true);
    messageInput.value = '';
    showBubble('Hmm... 🤔', 10000);

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();
        const reply = data.reply || 'Ehh Jeanny blur kejap 😅';

        addMessage(reply, false);

        const mood = detectMood(reply);
        setMood(mood);

        const shortReply = reply.length > 60 ? reply.substring(0, 60) + '...' : reply;
        showBubble(shortReply, 5000);

        if (mood === 'loving' || mood === 'excited') {
            spawnHearts(5);
        }

        setTimeout(() => {
            face.classList.add('blink');
            setTimeout(() => face.classList.remove('blink'), 300);
        }, 2000);

    } catch (error) {
        console.error('API Error:', error);
        showBubble('Alamak, error 😭', 3000);
    }
}

// ===== KEYBOARD =====
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// ===== IDLE BLINK =====
setInterval(() => {
    if (!isTalking && Math.random() < 0.3) {
        face.classList.add('blink');
        setTimeout(() => face.classList.remove('blink'), 300);
    }
}, 3000);

// ===== TAP CHARACTER =====
character.addEventListener('click', () => {
    const tapResponses = [
        'Hehe, kenapa? 🤭',
        'Abang ni! 😤💕',
        'Ada apa? 🥺',
        'Jeanny tak buat apa pun! 😏',
        'Ehh jangan kacau la! 🤭💕',
    ];
    const resp = tapResponses[Math.floor(Math.random() * tapResponses.length)];
    showBubble(resp, 3000);
    spawnHearts(3);
    setMood('playful');
});

// ===== IDLE =====
face.classList.add('idle');

// ===== GREETING =====
setTimeout(() => {
    showBubble('Hai abang! Jeanny rindu! 💕', 4000);
    setMood('loving');
    spawnHearts(3);
}, 1000);
