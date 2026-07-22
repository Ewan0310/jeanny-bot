// ========== JEANNY COMPANION APP.JS ==========

const chatBox = document.getElementById('chat-box');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const micBtn = document.getElementById('mic-btn');
const character = document.getElementById('character');
const moodText = document.getElementById('mood-text');

// ========== VOICE INPUT (Record → Whisper) ==========
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = async () => {
            stream.getTracks().forEach(t => t.stop());
            const blob = new Blob(audioChunks, { type: 'audio/webm' });
            
            if (blob.size < 500) {
                addMessage('Ehh tak dengar apa pun, cakap kuat sikit 😅', 'jeanny');
                return;
            }

            addMessage('🎤 Taipkan balik apa ko cakap...', 'system');

            try {
                const formData = new FormData();
                formData.append('audio', blob, 'voice.webm');

                const res = await fetch('/api/transcribe', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();

                removeSystemMessages();

                if (data.text && data.text.trim()) {
                    chatInput.value = data.text;
                    sendMessage();
                } else {
                    addMessage('Tak jelas la, cuba cakap lagi 🥺', 'jeanny');
                }
            } catch (err) {
                removeSystemMessages();
                addMessage('Audio error, try type je 💕', 'jeanny');
            }
        };

        mediaRecorder.start();
        isRecording = true;
        micBtn.classList.add('listening');
        micBtn.textContent = '🔴';
        character.classList.add('speaking');
        addMessage('🎤 Mendengar...', 'system');

    } catch (err) {
        console.error('Mic error:', err);
        addMessage('Kena bagi permission mic dulu! 🎤', 'jeanny');
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        micBtn.classList.remove('listening');
        micBtn.textContent = '🎤';
        character.classList.remove('speaking');
        removeSystemMessages();
    }
}

// ========== VOICE OUTPUT (TTS) ==========
function speakText(text) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();

    const cleanText = text.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}💕❤️🥺😊😏🔥💀~]/gu, '').trim();
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = 'ms-MY';
    utterance.rate = 1.0;
    utterance.pitch = 1.4;

    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => v.lang.startsWith('ms')) ||
                      voices.find(v => v.lang.startsWith('id')) ||
                      voices.find(v => v.name.includes('Female'));
    if (preferred) utterance.voice = preferred;

    utterance.onstart = () => character.classList.add('speaking');
    utterance.onend = () => character.classList.remove('speaking');

    window.speechSynthesis.speak(utterance);
}

if ('speechSynthesis' in window) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}

// ========== MIC BUTTON ==========
if (micBtn) {
    micBtn.addEventListener('click', () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    });
}

// ========== CHAT FUNCTIONS ==========
function addMessage(text, sender) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    if (sender === 'system') {
        div.style.fontStyle = 'italic';
        div.style.opacity = '0.6';
        div.style.textAlign = 'center';
    }
    div.textContent = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
    return div;
}

function removeSystemMessages() {
    document.querySelectorAll('.message.system').forEach(el => el.remove());
}

function setMood(mood) {
    const moods = {
        'happy': '😊 Happy', 'flirty': '😏 Flirty', 'excited': '🤩 Excited',
        'caring': '🥰 Caring', 'playful': '😜 Playful', 'shy': '😳 Shy',
        'sad': '🥺 Sedih', 'angry': '😤 Marah'
    };
    if (moodText) moodText.textContent = moods[mood] || '💕 Jeanny';
}

function animateReaction(type) {
    character.classList.remove('bounce', 'shake', 'blush');
    void character.offsetWidth;
    character.classList.add(type);
    setTimeout(() => character.classList.remove(type), 1000);
}

async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    addMessage(message, 'user');
    chatInput.value = '';

    const typingDiv = addMessage('Jeanny taip...', 'typing');
    typingDiv.style.fontStyle = 'italic';
    typingDiv.style.opacity = '0.5';
    character.classList.add('thinking');

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });
        const data = await response.json();

        typingDiv.remove();
        character.classList.remove('thinking');
        addMessage(data.reply, 'jeanny');
        speakText(data.reply);

        const reply = data.reply.toLowerCase();
        if (reply.includes('😏') || reply.includes('nakal')) {
            setMood('flirty'); animateReaction('blush');
        } else if (reply.includes('🥺') || reply.includes('sedih')) {
            setMood('sad');
        } else if (reply.includes('haha') || reply.includes('😜')) {
            setMood('playful'); animateReaction('bounce');
        } else if (reply.includes('💕') || reply.includes('sayang')) {
            setMood('caring'); animateReaction('bounce');
        } else {
            setMood('happy');
        }
    } catch (error) {
        typingDiv.remove();
        character.classList.remove('thinking');
        addMessage('Ehh Jeanny terputus kejap 🥺 Cuba lagi~', 'jeanny');
    }
}

// ========== EVENT LISTENERS ==========
sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// ========== IDLE ANIMATIONS ==========
setInterval(() => {
    if (!character.classList.contains('speaking') && !character.classList.contains('thinking')) {
        character.classList.add('idle-bounce');
        setTimeout(() => character.classList.remove('idle-bounce'), 2000);
    }
}, 5000);

// Welcome
setTimeout(() => {
    addMessage('Hai abang! Jeanny dah sini~ 💕', 'jeanny');
    speakText('Hai abang! Jeanny dah sini~');
}, 1500);
