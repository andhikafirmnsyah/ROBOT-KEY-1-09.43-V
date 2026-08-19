import time
import threading
from google import genai
import config

# ==========================================
# ERROR CLASSIFICATION CONSTANTS
# ==========================================
ERR_RATE_LIMIT = "RATE_LIMIT"
ERR_AUTH = "AUTH"
ERR_SERVER = "SERVER"
ERR_NETWORK = "NETWORK"
ERR_TIMEOUT = "TIMEOUT"
ERR_PARSE = "PARSE"
ERR_APPLICATION = "APPLICATION"
ERR_UNKNOWN = "UNKNOWN"

# ==========================================
# SMART KEY ROTATOR & HEALTH TRACKER
# ==========================================
api_pool = []
for key in config.API_KEYS:
    api_pool.append({
        "key": key,
        "status": "READY",        # READY, COOLDOWN, FAILED
        "health": 100,            # 0-100
        "cooldown_until": 0,
        "success_count": 0,
        "failure_count": 0,
        "last_error": None,
        "last_error_class": None,
        "last_used_at": 0,
        "last_success_at": 0,
        "last_failure_at": 0
    })

current_index = 0
lock = threading.Lock()

def classify_error(e):
    """Filter Klasifikasi Error P0-2"""
    err_str = str(e).lower()
    err_type = type(e).__name__

    # 1. Klasifikasi Internal / App Error
    if "jsondecode" in err_type.lower():
        return ERR_PARSE
    if err_type in ["ValueError", "TypeError", "KeyError", "AttributeError"]:
        return ERR_APPLICATION

    # 2. Klasifikasi API / Network Error
    if "429" in err_str or "quota" in err_str or "rate limit" in err_str or "exhausted" in err_str:
        return ERR_RATE_LIMIT
    if "401" in err_str or "403" in err_str or "api key" in err_str or "auth" in err_str:
        return ERR_AUTH
    if "503" in err_str or "500" in err_str or "server" in err_str:
        return ERR_SERVER
    if "timeout" in err_str or "deadline" in err_str:
        return ERR_TIMEOUT
    if "connection" in err_str or "network" in err_str or "resolve" in err_str:
        return ERR_NETWORK

    return ERR_UNKNOWN

def get_current_key_index():
    return current_index

def get_gemini_client():
    global current_index
    with lock:
        for i in range(len(api_pool)):
            idx = (current_index + i) % len(api_pool)
            if api_pool[idx]["status"] == "READY":
                current_index = idx
                api_pool[idx]["last_used_at"] = time.time()
                return genai.Client(api_key=api_pool[idx]["key"])
        
        print("[ENGINE ROOM] ALARM DARURAT! Bypass paksa dengan key terakhir...")
        return genai.Client(api_key=api_pool[current_index]["key"])

def record_success():
    """Memulihkan health secara bertahap setiap kali request sukses."""
    global current_index
    with lock:
        key_data = api_pool[current_index]
        key_data["success_count"] += 1
        key_data["last_success_at"] = time.time()
        # Recovery bertahap lambat (+5) agar tidak terlalu agresif
        if key_data["health"] < 100:
            key_data["health"] = min(100, key_data["health"] + 5)

def handle_api_error(e):
    """
    Decision Policy untuk Rotasi dan Health Penalty.
    Returns: (should_rotate, new_client)
    """
    global current_index
    with lock:
        key_data = api_pool[current_index]
        err_class = classify_error(e)
        now = time.time()

        key_data["last_error"] = str(e)
        key_data["last_error_class"] = err_class
        key_data["last_failure_at"] = now
        key_data["failure_count"] += 1

        print(f"[CIRCUIT BREAKER] Deteksi Error: {err_class} pada Kunci #{current_index}")

        # DECISION MATRIX P0-2
        if err_class in [ERR_PARSE, ERR_APPLICATION]:
            # JANGAN ROTATE & JANGAN KURANGI HEALTH
            return False, None

        should_rotate = True

        if err_class == ERR_RATE_LIMIT:
            key_data["health"] -= 30
            key_data["status"] = "COOLDOWN"
            key_data["cooldown_until"] = now + 3600 # 1 jam
        elif err_class == ERR_AUTH:
            key_data["health"] = 0
            key_data["status"] = "FAILED" # Auth invalid, jangan pernah dipakai lagi
        elif err_class == ERR_SERVER:
            key_data["health"] -= 20
            if key_data["health"] <= 0:
                key_data["status"] = "COOLDOWN"
                key_data["cooldown_until"] = now + 600 # 10 menit
        elif err_class in [ERR_NETWORK, ERR_TIMEOUT]:
            key_data["health"] -= 10
            if key_data["health"] <= 0:
                key_data["status"] = "COOLDOWN"
                key_data["cooldown_until"] = now + 300 # 5 menit
        else: # ERR_UNKNOWN
            key_data["health"] -= 25
            if key_data["health"] <= 0:
                key_data["status"] = "COOLDOWN"
                key_data["cooldown_until"] = now + 900 # 15 menit

        # Pemindahan Beban (Shift)
        if should_rotate:
            for i in range(1, len(api_pool) + 1):
                next_idx = (current_index + i) % len(api_pool)
                if api_pool[next_idx]["status"] == "READY":
                    current_index = next_idx
                    api_pool[current_index]["last_used_at"] = now
                    print(f"[ROTATOR] Pindah ke Kunci #{current_index}")
                    return True, genai.Client(api_key=api_pool[current_index]["key"])
            
            # Jika semua key habis
            return True, genai.Client(api_key=api_pool[current_index]["key"])

        return False, None

# ==========================================
# BACKGROUND RECOVERY (PEMULIHAN DIAM-DIAM)
# ==========================================
def recovery_worker():
    while True:
        time.sleep(60)
        with lock:
            now = time.time()
            for idx, key_data in enumerate(api_pool):
                if key_data["status"] == "COOLDOWN" and now > key_data["cooldown_until"]:
                    # JANGAN recovery kunci yang Auth Failed
                    if key_data["last_error_class"] != ERR_AUTH:
                        print(f"[BACKGROUND RECOVERY] Kunci #{idx} pulih. Bergabung kembali.")
                        key_data["status"] = "READY"
                        # Recover tidak langsung 100, tapi 80 (Konservatif)
                        key_data["health"] = 80 

worker_thread = threading.Thread(target=recovery_worker, daemon=True)
worker_thread.start()
