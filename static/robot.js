let audioCtx;
function initAudio() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === 'suspended') audioCtx.resume();
}

// === ROBOT VOCALIZATION ENGINE ===
function playRobotVoice(emotion, intensity, energy) {
    if (!audioCtx) return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain); gain.connect(audioCtx.destination);
    let now = audioCtx.currentTime;
    let type = 'sine'; let baseFreq = 800;
    let duration = 0.05 + ((energy || 5) * 0.01);
    let volume = ((intensity || 5) * 0.03);

    switch(emotion) {
        case 'happy': type = 'sine'; baseFreq = 1000 + Math.random() * 500; break;
        case 'sad': type = 'triangle'; baseFreq = 400 + Math.random() * 100; duration *= 1.5; break;
        case 'angry': type = 'sawtooth'; baseFreq = 200 + Math.random() * 200; volume *= 1.2; break;
        case 'surprised': type = 'square'; baseFreq = 1500; break;
        case 'confused': type = 'triangle'; baseFreq = 600 + (Math.random() > 0.5 ? 200 : -200); break;
        case 'sleepy': type = 'sine'; baseFreq = 300; duration *= 2; volume *= 0.4; break;
        case 'smug': type = 'square'; baseFreq = 800 + Math.random() * 100; break;
        case 'alarm_high': type = 'square'; baseFreq = 2000; duration = 0.2; volume = 0.5; break;
        case 'alarm_low': type = 'sawtooth'; baseFreq = 800; duration = 0.2; volume = 0.5; break;
        case 'heal_beep': type = 'sine'; baseFreq = 1200; duration = 0.1; volume = 0.2; break;
        default: type = 'sine'; baseFreq = 700 + Math.random() * 300; break;
    }

    osc.type = type; osc.frequency.setValueAtTime(baseFreq, now);
    if (emotion === 'curious' || emotion === 'surprised' || emotion === 'confused') osc.frequency.exponentialRampToValueAtTime(baseFreq + (intensity * 50), now + duration);
    else if (emotion === 'sad' || emotion === 'sleepy' || emotion === 'bored') osc.frequency.exponentialRampToValueAtTime(Math.max(100, baseFreq - (intensity * 20)), now + duration);

    gain.gain.setValueAtTime(volume, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + duration);
    osc.start(now); osc.stop(now + duration);
}

const face = document.getElementById('robotFace');
const eyeL = document.getElementById('eyeLeft');
const eyeR = document.getElementById('eyeRight');
const ledMic = document.getElementById('ledMic');
const ledAi = document.getElementById('ledAi');
const dynamicStyleTag = document.getElementById('ai-dynamic-styles');

let currentEmotion = 'neutral';
let isSpeaking = false;
let isAsleep = false;
let sleepTimeout;
let isSystemStarted = false;
let isAlarmRinging = false;
let isHealing = false;
let alarmInterval;

function applyAiState(state) {
    if (isHealing) return;
    currentEmotion = state.emotion || 'neutral';
    face.className = 'face';
    if(!isAsleep && isSystemStarted && !isAlarmRinging) face.classList.add('listening');
    
    if (state.animation && state.animation !== 'none') {
        face.classList.add(`anim-${state.animation}`);
        setTimeout(() => face.classList.remove(`anim-${state.animation}`), 600);
    }
    if (currentEmotion === 'angry' || currentEmotion === 'error') face.classList.add('angry-mode');
    
    eyeL.style.transform = 'none'; eyeR.style.transform = 'none';
    let microExp = (state.energy > 7 && state.emotion !== 'sleepy') ? ' high-energy' : '';
    eyeL.className = `eye left ${currentEmotion}${microExp}`;
    eyeR.className = `eye right ${currentEmotion}${microExp}`;
}

// === ANIMASI DIAM & BERKEDIP ===
const idleAnimations = [{l: 'translate(-25px, 0)', r: 'translate(-25px, 0)'}, {l: 'translate(25px, 0)', r: 'translate(25px, 0)'}, {l: 'translate(0, -25px)', r: 'translate(0, -25px)'}, {l: 'translate(0, 25px)', r: 'translate(0, 25px)'}, {l: 'none', r: 'none'}];
setInterval(() => {
    if (!isSpeaking && !isAsleep && isSystemStarted && !isAlarmRinging && !isHealing) {
        if (Math.random() > 0.7 && currentEmotion === 'neutral') {
            const anim = idleAnimations[Math.floor(Math.random() * idleAnimations.length)];
            eyeL.style.transform = anim.l; eyeR.style.transform = anim.r;
        }
    }
}, 1500);

function blink() {
    if (!isSpeaking && currentEmotion !== 'sleepy' && currentEmotion !== 'thinking' && !isHealing && eyeL.style.transform === 'none') {
        eyeL.classList.add('closed'); eyeR.classList.add('closed');
        setTimeout(() => { eyeL.classList.remove('closed'); eyeR.classList.remove('closed'); }, 150);
    }
    setTimeout(blink, Math.random() * 3000 + 1500);
}
setTimeout(blink, 1000);

// === SISTEM TIDUR & DARURAT ===
function putToSleep() {
    if(!isAsleep && !isSpeaking && !isAlarmRinging && !isHealing) {
        isAsleep = true; face.classList.remove('listening'); ledMic.classList.remove('mic-on');
        applyAiState({emotion: 'sleepy', energy: 1});
        document.getElementById('replyBox').innerHTML = "";
        document.getElementById('transcriptBox').innerText = "[ Zzz... Panggil 'Keyy' untuk membangunkan ]";
    }
}
function wakeUpRobot() {
    isAsleep = false; face.classList.add('listening'); ledMic.classList.add('mic-on');
    applyAiState({emotion: 'surprised', energy: 8}); playRobotVoice('happy', 8, 8); resetSleepTimer();
}
function resetSleepTimer() { clearTimeout(sleepTimeout); sleepTimeout = setTimeout(putToSleep, 20000); }

function triggerFindMeAlarm() {
    if (isAlarmRinging || isHealing) return;
    isAlarmRinging = true; isAsleep = false; clearTimeout(sleepTimeout);
    ledAi.className = 'led error'; applyAiState({emotion: 'surprised', energy: 10, animation: 'shake'});
    document.getElementById('transcriptBox').innerText = "[ RADAR DARURAT AKTIF ]";
    document.getElementById('replyBox').innerHTML = "BIP! SAYA DI SINI KOMANDAN!!!";
    document.getElementById('replyBox').style.color = "#ff3333";
    alarmInterval = setInterval(() => {
        playRobotVoice('alarm_high', 10, 10); setTimeout(() => playRobotVoice('alarm_low', 10, 10), 250);
        face.classList.toggle('angry-mode');
    }, 500);
}
function stopAlarm() {
    if (isAlarmRinging) {
        isAlarmRinging = false; clearInterval(alarmInterval);
        face.classList.remove('angry-mode'); ledAi.className = 'led';
        document.getElementById('replyBox').style.color = "#fff";
        typeTextAuto({text: "Bip! Mode darurat dimatikan.", emotion: "happy", intensity: 6, energy: 7});
        resetSleepTimer();
    }
}

// === FITUR AUTO-HEAL (PEMBERSIH BUG) ===
window.triggerAutoHeal = function() {
    if (isHealing) return;
    isHealing = true; isAsleep = false; clearTimeout(sleepTimeout);
    
    dynamicStyleTag.innerHTML = ""; 
    
    face.classList.add('angry-mode'); ledAi.className = 'led error';
    document.getElementById('transcriptBox').innerText = "[ RESET / AUTO-HEAL INITIATED ]";
    document.getElementById('replyBox').style.color = "#ff3333";
    document.getElementById('replyBox').innerHTML = "MEMBERSIHKAN BUG & RESET KE SETELAN ORISINAL...";
    playRobotVoice('angry', 10, 10);
    eyeL.className = 'eye left closed'; eyeR.className = 'eye right closed';
    
    setTimeout(() => {
        document.getElementById('replyBox').innerHTML = "Rebooting UI core... [||||      ] 50%";
        playRobotVoice('heal_beep', 5, 5); eyeL.className = 'eye left confused'; eyeR.className = 'eye right confused';
    }, 1500);
    
    setTimeout(() => {
        isHealing = false; face.classList.remove('angry-mode'); ledAi.className = 'led';
        document.getElementById('replyBox').style.color = "#fff";
        applyAiState({emotion: 'happy', energy: 8, animation: 'bounce'});
        playRobotVoice('happy', 8, 8);
        typeTextAuto({text: "Sistem pulih! UI kembali ke setelan sempurna Komandan!", emotion: "happy", intensity: 8, energy: 8});
        resetSleepTimer();
        if (isSystemStarted) { try { recognition.start(); } catch(e) {} }
    }, 3500);
}

// === ZOMBIE MIC (PANTANG MATI & AGRESIF) ===
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
if (SpeechRecognition) {
    recognition = new SpeechRecognition(); recognition.lang = 'id-ID';
    recognition.continuous = true; recognition.interimResults = false;
    recognition.onstart = function() {
        if(!isAsleep && isSystemStarted && !isAlarmRinging && !isHealing) {
            face.classList.add('listening'); ledMic.classList.add('mic-on');
        }
    };
    recognition.onresult = function(event) {
        let currentTranscript = event.results[event.results.length - 1][0].transcript.trim().toLowerCase();
        if (isHealing) return;
        
        if (isAlarmRinging) {
            if (/ketemu|stop|berhenti|oke|udah|mati/i.test(currentTranscript)) stopAlarm();
            return;
        }
        
        if (/reset|setelan awal|kembali normal|default|hapus bug/i.test(currentTranscript)) {
            triggerAutoHeal(); return;
        }
        
        if (isAsleep) {
            if (/key|kei|ki|kay|ke|robot|bot|woy|woi|oy|oi|halo|hei|helo|bangun|tes|test/i.test(currentTranscript)) {
                wakeUpRobot();
                let command = currentTranscript.replace(/key|kei|ki|kay|ke|robot|bot|woy|woi|oy|oi|halo|hei|helo|bangun|tes|test/gi, "").trim();
                if (/di mana|dimana|posisi|hilang|kamu di mana/i.test(command)) { triggerFindMeAlarm(); return; }
                
                if (command.length > 2) {
                    document.getElementById('transcriptBox').innerText = `[User]: "${command}"`; 
                    askDecisionEngine(command);
                } else {
                    document.getElementById('transcriptBox').innerText = "[User membangunkan Robot Key]";
                    typeTextAuto({text: "Bip! Siap Komandan! Ada yang bisa dibantu?", emotion: "happy", intensity: 7, energy: 8});
                }
            } else {
                document.getElementById('transcriptBox').innerText = `[Ngigau dengar: "${currentTranscript}"]`;
            }
        } else {
            if (/di mana|dimana|posisi|hilang|kamu di mana/i.test(currentTranscript)) { triggerFindMeAlarm(); return; }
            resetSleepTimer();
            document.getElementById('transcriptBox').innerText = `[User]: "${currentTranscript}"`;
            askDecisionEngine(currentTranscript);
        }
    };
    recognition.onerror = function(event) {
        if (event.error === 'not-allowed') { isSystemStarted = false; ledMic.classList.remove('mic-on'); }
    };
    recognition.onend = function() {
        if (isSystemStarted && !isHealing) {
            setTimeout(() => { try { recognition.start(); } catch(e) {} }, 250);
        }
    };
}

function toggleMic() {
    initAudio();
    if (isHealing) return;
    if (isAlarmRinging) { stopAlarm(); return; }
    
    isSystemStarted = true; isAsleep = false; resetSleepTimer();
    document.getElementById('replyBox').innerHTML = "";
    try { recognition.start(); } catch(e) {}
    face.classList.add('listening'); ledMic.classList.add('mic-on');
    applyAiState({emotion: 'happy', energy: 7}); playRobotVoice('happy', 5, 5);
}

// === DECISION ENGINE & SELF-PROGRAMMING ===
async function askDecisionEngine(userText) {
    ledAi.className = 'led ai-on'; applyAiState({emotion: 'thinking', energy: 5});
    try {
        const response = await fetch('/chat', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ message: userText || "" }) 
        });
        const data = await response.json();
        
        if (data.css_inject && data.css_inject !== "" && data.css_inject !== "none") {
            dynamicStyleTag.innerHTML += `\n${data.css_inject}`;
            playRobotVoice('surprised', 10, 10);
        }
        
        if (data.js_inject && data.js_inject !== "" && data.js_inject !== "none") {
            setTimeout(() => { try { eval(data.js_inject); } catch(e) { console.error("Error JS", e); } }, 2000);
        }
        
        ledAi.className = 'led'; applyAiState(data);
        typeTextAuto(data);
    } catch (error) {
        triggerAutoHeal();
    }
}

// === AUTO TYPING ===
function typeTextAuto(state) {
    isSpeaking = true; resetSleepTimer();
    const rBox = document.getElementById('replyBox'); 
    const rWrap = document.getElementById('replyWrapper');
    rBox.style.color = (state.emotion === 'angry' || state.emotion === 'error') ? "#ff3333" : "#fff";
    rBox.innerHTML = "";
    let text = state.text || ""; let i = 0; 
    let speed = 60 - ((state.energy || 5) * 4); if (speed < 15) speed = 15;
    
    function typeWriter() {
        if (isAlarmRinging || isHealing) return;
        if (i < text.length) {
            let char = text.charAt(i);
            rBox.innerHTML = text.substring(0, i + 1) + '<span class="cursor"></span>';
            rWrap.scrollTop = rWrap.scrollHeight;
            if (i % 2 === 0 && char.trim() !== '') playRobotVoice(state.emotion || 'neutral', state.intensity || 5, state.energy || 5);
            i++; setTimeout(typeWriter, speed);
        } else {
            isSpeaking = false; ledAi.className = 'led'; rBox.innerHTML = text; resetSleepTimer();
        }
    }
    setTimeout(typeWriter, 200);
}
