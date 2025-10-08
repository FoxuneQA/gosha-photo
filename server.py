from flask import Flask, request, jsonify, send_file, abort, render_template_string
import os, uuid
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXT = {'png', 'jpg', 'jpeg'}

app = Flask(__name__, static_folder='.', static_url_path='')

# Простое хранилище одноразовых токенов: token -> срок жизни (UTC)
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

# Подгружаем HTML-шаблон с маркером {{TOKEN}}
with open('index.html', 'r', encoding='utf-8') as f:
    INDEX_HTML = f.read()

@app.route('/new')
def new_link():
    """Открой /new — получишь готовую ссылку с токеном."""
    ttl = int(request.args.get('ttl', 60))  # срок жизни, минут
    token = create_token(ttl)
    link = request.host_url.rstrip('/') + '/' + token
    return f"""
    <h2>Ссылка готова ✅</h2>
    <p>Срок жизни: {ttl} мин.</p>
    <p><a href="{link}" target="_blank" rel="noopener">{link}</a></p>
    <p>Отправь её человеку. Он откроет, даст разрешение на камеру, сделает фото — файл сохранится в <code>uploads/</code>.</p>
    """

@app.route('/<token>')
def serve_page(token):
    if not token_valid(token):
        return "Ссылка недействительна или просрочена.", 404
    html = INDEX_HTML.replace("{{TOKEN}}", token)
    return render_template_string(html)

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'photo' not in request.files or 'token' not in request.form:
        return jsonify({'error': 'photo and token required'}), 400

    token = request.form['token']
    if not token_valid(token):
        return jsonify({'error': 'invalid or expired token'}), 403

    file = request.files['photo']
    ext = file.filename.rsplit('.',1)[-1].lower() if '.' in file.filename else 'png'
    if ext not in ALLOWED_EXT:
        ext = 'png'

    name = f"photo_{token}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}"
    path = os.path.join(UPLOAD_DIR, secure_filename(name))
    file.save(path)

    # Делаем токен одноразовым (если нужно много фото по одной ссылке — удали эту строку)
    tokens.pop(token, None)

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