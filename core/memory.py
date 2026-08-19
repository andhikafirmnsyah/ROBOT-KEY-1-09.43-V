import json
import os
import config
import threading

# ==========================================
# MEMORI 3 LAPIS, COMPRESSION, & THREAD-SAFE LOCK
# ==========================================

# Gunakan RLock (Reentrant Lock) untuk keamanan nested calls
memory_lock = threading.RLock()

def get_empty_memory():
    """Struktur dasar The Engine Room: 3 Lapis Memori"""
    return {
        "messages": [],     # Lapis 1: Obrolan Aktif (Kena Kompresi)
        "facts": {          # Lapis 2: Profil & Preferensi (Permanen)
            "identity": "Komandan / Bang",
            "preferences": [] 
        },       
        "experiences": []   # Lapis 3: Logika Perbaikan & Sistem (Otonom)
    }

def load_memory():
    """Memuat ingatan dari brankas lokal secara Thread-Safe"""
    with memory_lock:
        if os.path.exists(config.MEMORY_FILE):
            try:
                with open(config.MEMORY_FILE, 'r') as f: 
                    data = json.load(f)
                    # Auto-Migrasi
                    if isinstance(data, list):
                        new_mem = get_empty_memory()
                        new_mem["messages"] = data
                        return new_mem
                    return data
            except Exception:
                print("[MEMORY] File korup! Memulai format memori 3 lapis...")
                return get_empty_memory()
        return get_empty_memory()

def compress_context(messages):
    """Context Compression: Meringkas riwayat agar tidak boros token"""
    if len(messages) > config.MAX_MEMORY_HISTORY:
        print("[MEMORY] Memori obrolan terlalu panjang! Melakukan kompresi token...")
        return messages[:2] + messages[-(config.MAX_MEMORY_HISTORY - 2):]
    return messages

def save_memory(memory_data):
    """Menyimpan dengan Atomic Write & Thread-Safe Lock"""
    with memory_lock:
        os.makedirs(os.path.dirname(config.MEMORY_FILE), exist_ok=True)
        
        if "messages" in memory_data:
            memory_data["messages"] = compress_context(memory_data["messages"])
            
        temp_file = config.MEMORY_FILE + ".tmp"
        try:
            # Tulis ke file temporary terlebih dahulu
            with open(temp_file, 'w') as f: 
                json.dump(memory_data, f, indent=4)
                f.flush()
                os.fsync(f.fileno()) # Atomic Guarantee: Paksa tulis ke disk fisik
                
            # Replace secara atomik
            os.replace(temp_file, config.MEMORY_FILE)
        except Exception as e:
            print(f"[MEMORY ERROR] Gagal menyegel brankas memori: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

def add_transaction(user_text, model_text):
    """Menambahkan pasangan obrolan USER + MODEL secara atomik (P0-3.1)"""
    with memory_lock:
        mem = load_memory()
        if "messages" not in mem:
            mem["messages"] = []
        
        # Dijamin masuk berurutan tanpa bisa disela
        mem["messages"].append({"role": "user", "parts": user_text})
        mem["messages"].append({"role": "model", "parts": model_text})
        save_memory(mem)

