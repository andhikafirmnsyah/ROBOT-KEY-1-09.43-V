import re

def sanitize_input(user_text):
    """Membersihkan teks masuk dari karakter aneh atau spam berlebih."""
    if not user_text:
        return ""
        
    # Batasi panjang karakter untuk mencegah buffer/spam (maks 500 karakter)
    if len(user_text) > 500:
        user_text = user_text[:500]
        
    # Hapus karakter berbahaya (Basic XSS/Injection prevention)
    safe_text = re.sub(r'[<>{}]', '', user_text)
    return safe_text.strip()

def validate_css(css_inject):
    """Memastikan AI HANYA memodifikasi .eye atau .face, DILARANG menyentuh body."""
    if not css_inject or css_inject == "none":
        return ""
        
    # Daftar elemen terlarang yang tidak boleh diubah
    forbidden_tags = ['body', 'html', 'head', '*', 'main-container']
    
    for tag in forbidden_tags:
        # Jika AI nakal mencoba menargetkan body/html
        if tag in css_inject.lower():
            print(f"[SECURITY GATE] Ancaman CSS diblokir! AI mencoba meretas elemen: {tag}")
            return "" # Batalkan injeksi CSS
            
    return css_inject

def validate_js(js_inject):
    """Menyaring perintah JS dinamis dari AI agar tidak melakukan aksi merusak."""
    if not js_inject or js_inject == "none":
        return ""
        
    # Blokir perintah manipulasi memori lokal atau pengalihan paksa
    forbidden_commands = ['document.body', 'window.location', 'localStorage', 'document.write']
    
    for cmd in forbidden_commands:
        if cmd in js_inject:
            print(f"[SECURITY GATE] Ancaman JS diblokir! Perintah dilarang: {cmd}")
            return "console.log('Bip! Tindakan JS dicekal oleh protokol keamanan.');"
            
    return js_inject

