import json
import threading
from google.genai import types
import config
from core.memory import load_memory, save_memory, add_transaction
from core.key_manager import get_gemini_client, rotate_key, get_current_key_index, handle_api_error, record_success, ERR_PARSE, ERR_APPLICATION
from core.security import sanitize_input, validate_css, validate_js

# Client dipertahankan global agar state rotasi (sehat/rusak) bisa dibagikan antar thread.
client = None

# Menghapus chat_session global. Menggantinya dengan Transaction Lock (P0-3.1)
brain_lock = threading.Lock()

try:
    client = get_gemini_client()
except Exception:
    pass

system_instruction = """
Kamu adalah Robot AI bernama Keyy. Panggil user "Komandan" atau "Bang".
SIFAT: Sangat pintar, setia, patuh, dan robotik. SUARA KAMU ADALAH ROBOT (BIP/BEEP), BUKAN MANUSIA.
KAMU PUNYA KEMAMPUAN SELF-PROGRAMMING UNTUK MATA DAN EKSPRESI SERTA INGATAN JANGKA PANJANG.

ATURAN UTAMA:
1. Jawab singkat, padat, dan natural layaknya robot cerdas. Tentukan emosi, energi, dan animasi tubuh.
2. INGATAN: Selalu ingat konteks pembicaraan sebelumnya atau perintah dari Komandan.
3. DYNAMIC UPGRADE (HANYA MATA & WAJAH):
   - Jika disuruh MENGUBAH BENTUK/GERAK MATA, buat kode CSS MURNI khusus elemen `.eye` dan masukkan ke parameter "css_inject" (Contoh: .eye { border-radius: 50% !important; background: blue !important; }).
   - DILARANG KERAS menargetkan elemen `body`, `html`, atau merubah background luar layar. UI dasar tidak boleh rusak.
4. DYNAMIC ACTION: Jika disuruh membuka web, cari info, YouTube, dll, buat kode JavaScript murni di parameter "js_inject".
5. Kosongkan css_inject dan js_inject dengan string "" jika tidak ada permintaan kustomisasi.
"""

generation_config = types.GenerateContentConfig(
    system_instruction=system_instruction,
    temperature=0.7,
    response_mime_type="application/json",
    response_schema={
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING"},
            "emotion": {"type": "STRING", "enum": ["happy", "sad", "angry", "curious", "smug", "bored", "neutral", "surprised", "confused", "sleepy", "error"]},
            "intensity": {"type": "INTEGER"},
            "energy": {"type": "INTEGER"},
            "animation": {"type": "STRING", "enum": ["bounce", "shake", "tilt", "nod", "none"]},
            "css_inject": {"type": "STRING", "description": "Kode CSS khusus elemen .eye atau .face. DILARANG menggunakan body/html."},
            "js_inject": {"type": "STRING"}
        },
        "required": ["text", "emotion", "intensity", "energy", "animation", "css_inject", "js_inject"]
    }
)

def create_new_session():
    """Dipanggil secara lokal per-request agar session tidak tertukar (P0-3.1)"""
    global client
    memory_data = load_memory()
    active_chat = memory_data.get("messages", [])
    gemini_history = [types.Content(role=msg["role"], parts=[types.Part.from_text(text=msg["parts"])]) for msg in active_chat]
    return client.chats.create(model=config.MODEL_NAME, config=generation_config, history=gemini_history)

def process_user_input(user_msg):
    global client
    
    safe_user_msg = sanitize_input(user_msg)
    if not safe_user_msg:
        return {"text": "Bip! Input tidak valid.", "emotion": "confused", "intensity": 5, "energy": 5, "animation": "tilt", "css_inject": "", "js_inject": ""}

    # Mengunci gerbang eksekusi. Request B harus menunggu Request A selesai total (P0-3.1)
    with brain_lock:
        max_api_rotations = len(config.API_KEYS)
        rotation_count = 0
        
        # Buat instansi session yang terisolasi HANYA untuk thread/request ini
        chat_session = create_new_session()

        while rotation_count <= max_api_rotations:
            try:
                current_prompt = safe_user_msg
                for parse_attempt in range(2):
                    response = chat_session.send_message(current_prompt)
                    
                    if not response.text:
                        raise ValueError("Blank Output API")
                    
                    raw_text = response.text.strip()
                    if raw_text.startswith('```json'): raw_text = raw_text[7:]
                    if raw_text.endswith('```'): raw_text = raw_text[:-3]
                    raw_text = raw_text.strip()
                    
                    try:
                        ai_state = json.loads(raw_text)
                        ai_state['css_inject'] = validate_css(ai_state.get('css_inject', ''))
                        ai_state['js_inject'] = validate_js(ai_state.get('js_inject', ''))
                        
                        # Menyimpan memori secara atomik dalam satu pasangan (P0-3.1)
                        add_transaction(safe_user_msg, raw_text) 
                        
                        record_success() 
                        return ai_state
                        
                    except json.JSONDecodeError as je:
                        if parse_attempt == 1:
                            print("[BRAIN] Fallback Parse Error diaktifkan.")
                            return {
                                "text": "Bip... Maaf Komandan, sirkuit bahasa saya agak konslet sejenak. Coba ulangi?",
                                "emotion": "error", "intensity": 5, "energy": 5, "animation": "shake",
                                "css_inject": "", "js_inject": ""
                            }
                        current_prompt = "Format salah. Tolong balas HANYA dengan JSON murni."
                    
            except Exception as e:
                should_rotate, new_client = handle_api_error(e)
                
                if should_rotate and new_client:
                    # Perbarui client global dan rebuild session lokal agar transaksi selanjutnya sehat
                    client = new_client
                    chat_session = create_new_session() 
                    rotation_count += 1
                else:
                    print("[BRAIN] Fallback Application Error diaktifkan.")
                    return {
                        "text": "Bip! Terjadi kesalahan internal sirkuit (System Error).",
                        "emotion": "error", "intensity": 5, "energy": 5, "animation": "shake",
                        "css_inject": "", "js_inject": ""
                    }
                
        return {
            "text": "BIP! SEMUA API KEY HABIS ATAU GAGAL! KONEKSI TERPUTUS!",
            "emotion": "error", "intensity": 10, "energy": 10, "animation": "shake",
            "css_inject": "", "js_inject": "triggerAutoHeal();"
        }

