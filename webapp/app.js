// ========== JEANNY COMPANION APP.JS (WITH VOICE) ==========

const chatBox = document.getElementById('chat-box');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const micBtn = document.getElementById('mic-btn');
const character = document.getElementById('character');
const moodText = document.getElementById('mood-text');

// ========== SPEECH SETUP ==========
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isListening = false;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'ms-MY'; // Bahasa Melayu
    
    recognition.onstart = () => {
        isListening = true;
        micBtn.classList.add('listening');
        micBtn.textContent = '🔴';
        character.classList.add('speaking');
        addMessage('🎤 Mendengar...', 'system');
    };
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        chatInput.value = transcript;
        removeSystemMessages();
        sendMessage();
    };
    
    recognition.onerror = (event) => {
        console.error('Speech error:', event.error);
        isListening = false;
        micBtn.classList.remove('listening');
        micBtn.textContent = '🎤';
        character.classList.remove('speaking');
        removeSystemMessages();
        if (event.error === 'not-allowed') {
            addMessage('Ehh kena bagi permission mic dulu 😅', 'jeanny');
        }
    };
    
    recognition.onend = () => {
        isListening = false;
        micBtn.classList.remove('listening');
        micBtn.textContent = '🎤';
        character.classList.remove('speaking');
        removeSystemMessages();
    };
} else {
    // Hide mic if browser doesn't support
    if (micBtn) micBtn.style.display = 'none';
}

// ========== VOICE OUTPUT (TTS) ==========
function speakText(text) {
    if (!('speechSynthesis' in window)) return;
    
    // Stop any ongoing speech
    window.speechSynthesis.cancel();
    
    // Clean text - remove emojis and special chars
    const cleanText = text.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}💕❤️🥺😊😏🔥💀~]/gu, '').trim();
    
    if (!cleanText) return;
    
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = 'ms-MY';
    utterance.rate = 1.0;
    utterance.pitch = 1.4; // Higher pitch = more feminine voice
    
    // Try to find Malay or female voice
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(v => v.lang.startsWith('ms')) || 
                           voices.find(v => v.name.includes('Female')) ||
                           voices.find(v => v.lang.startsWith('id')); // Indonesian close to Malay
    if (preferredVoice) utterance.voice = preferredVoice;
    
    utterance.onstart = () => {
        character.classList.add('speaking');
    };
    
    utterance.onend = () => {
        character.classList.remove('speaking');
    };
    
    window.speechSynthesis.speak(utterance);
}

// Load voices (some browsers need this)
if ('speechSynthesis' in window) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = () => {
        window.speechSynthesis.getVoices();
    };
}

// ========== MIC BUTTON ==========
if (micBtn) {
    micBtn.addEventListener('click', () => {
        if (!recognition) {
            addMessage('Browser ko tak support voice 😅', 'jeanny');
            return;
        }
        
        if (isListening) {
            recognition.stop();
        } else {
            try {
                recognition.start();
            } catch (e) {
                console.error('Mic error:', e);
                addMessage('Cuba tekan mic sekali lagi 🎤', 'jeanny');
            }
        }
    });
}

// ========== CHAT FUNCTIONS ==========
function addMessage(text, sender) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    
    if (sender === 'system') {
        div.className = 'message system';
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
        'happy': '😊 Happy',
        'flirty': '😏 Flirty', 
        'excited': '🤩 Excited',
        'caring': '🥰 Caring',
        'playful': '😜 Playful',
        'shy': '😳 Shy',
        'sad': '🥺 Sedih',
        'angry': '😤 Marah'
    };
    if (moodText) moodText.textContent = moods[mood] || '💕 Jeanny';
}

function animateReaction(type) {
    character.classList.remove('bounce', 'shake', 'blush');
    void character.offsetWidth; // Trigger reflow
    character.classList.add(type);
    setTimeout(() => character.classList.remove(type), 1000);
}

async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;
    
    // Add user message
    addMessage(message, 'user');
    chatInput.value = '';
    
    // Show typing
    const typingDiv = addMessage('Jeanny taip...', 'typing');
    typingDiv.style.fontStyle = 'italic';
    typingDiv.style.opacity = '0.5';
    
    // Animate thinking
    character.classList.add('thinking');
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        typingDiv.remove();
        character.classList.remove('thinking');
        
        // Add Jeanny reply
        addMessage(data.reply, 'jeanny');
        
        // Speak the reply
        speakText(data.reply);
        
        // Detect mood from reply
        const reply = data.reply.toLowerCase();
        if (reply.includes('😏') || reply.includes('nakal') || reply.includes('gatal')) {
            setMood('flirty');
            animateReaction('blush');
        } else if (reply.includes('🥺') || reply.includes('sedih')) {
            setMood('sad');
        } else if (reply.includes('haha') || reply.includes('😜')) {
            setMood('playful');
            animateReaction('bounce');
        } else if (reply.includes('💕') || reply.includes('sayang')) {
            setMood('caring');
            animateReaction('bounce');
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

// Welcome voice
setTimeout(() => {
    speakText('Hai sayang! Jeanny dah sini~');
}, 1500);
