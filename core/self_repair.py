import os
import shutil
import time
import glob

# Daftar file vital (UI dan Mesin Utama) yang tidak boleh hilang
CRITICAL_FILES = [
    'app.py',
    'config.py',
    'templates/index.html',
    'static/robot.css',
    'static/robot.js'
]

MAX_BACKUPS = 5 # Batas maksimal jumlah backup yang disimpan

def check_system_health():
    """Mendiagnosis keberadaan file-file penting sebelum sistem berjalan."""
    missing_files = []
    
    for file_path in CRITICAL_FILES:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"[DIAGNOSTIC] ALARM DARURAT! File inti hilang: {missing_files}")
        return False
        
    print("[DIAGNOSTIC] Cek Fisik Selesai. Semua file inti terpantau AMAN.")
    return True

def backup_memory():
    """Melakukan isolasi backup data memori Komandan dengan timestamp & rotasi."""
    memory_file = 'memory/robot_memory.json'
    backup_dir = 'backups/'
    
    os.makedirs(backup_dir, exist_ok=True)
    
    if os.path.exists(memory_file):
        try:
            # 1. Buat Backup Berdasarkan Waktu
            timestamp = time.strftime("%Y-%m-%d_%H%M%S")
            backup_filename = f"robot_memory_{timestamp}.json"
            backup_path = os.path.join(backup_dir, backup_filename)
            shutil.copy(memory_file, backup_path)
            print(f"[SELF-REPAIR] Memori Komandan berhasil di-backup ke {backup_filename}.")
            
            # 2. Cleanup (Retensi Backup)
            backups = sorted(glob.glob(os.path.join(backup_dir, "robot_memory_*.json")))
            while len(backups) > MAX_BACKUPS:
                oldest = backups.pop(0)
                os.remove(oldest)
                print(f"[SELF-REPAIR] Rotasi: Menghapus backup lama {os.path.basename(oldest)}")
                
        except Exception as e:
            # Tidak crash, hanya mencetak error
            print(f"[SELF-REPAIR] Peringatan: Gagal melakukan isolasi backup: {e}")
