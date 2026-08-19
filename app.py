from flask import Flask, request, jsonify, render_template
from core.brain import process_user_input
from core.self_repair import check_system_health, backup_memory

app = Flask(__name__)

# ==========================================
# STARTUP DIAGNOSTICS & BACKUP (PATCH 1)
# ==========================================
check_system_health()
backup_memory()
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.json.get('message', "")
    ai_state = process_user_input(user_msg)
    return jsonify(ai_state)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
