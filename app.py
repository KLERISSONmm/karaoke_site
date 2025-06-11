from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os, json, re, urllib.parse, requests
from pytubefix import YouTube

app = Flask(__name__)

DATA_FOLDER = "dados_karaoke"
IMAGE_FOLDER = os.path.join(DATA_FOLDER, "thumbnails")
os.makedirs(IMAGE_FOLDER, exist_ok=True)

YOUTUBE_API_KEY = "AIzaSyBmDrhtOmHN9Q4TJCfMfrOR-QSDiX7PiF8"

def sanitize_filename(title):
    return re.sub(r'[^\w\-_. ]', '', title)

def get_user_file(user):
    return os.path.join(DATA_FOLDER, f"{sanitize_filename(user)}.json")

def load_user_data(user):
    path = get_user_file(user)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_user_data(user, data):
    path = get_user_file(user)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def buscar_video_youtube(termo):
    query = urllib.parse.quote(termo)
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=1&q={query}+karaoke&key={YOUTUBE_API_KEY}"
    response = requests.get(url)
    data = response.json()
    if 'items' in data and len(data['items']) > 0:
        video = data['items'][0]
        video_id = video['id']['videoId']
        titulo = video['snippet']['title']
        thumb_url = video['snippet']['thumbnails']['high']['url']
        return {
            'id': video_id,
            'titulo': titulo,
            'link': f"https://www.youtube.com/watch?v={video_id}",
            'thumbnail_url': thumb_url
        }
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if request.method == 'POST':
        user = request.form['usuario'].strip()
        return redirect(url_for('perfil') + f"?usuario={user}")
    user = request.args.get('usuario')
    if not user:
        return redirect(url_for('index'))
    data = load_user_data(user)
    return render_template('karaoke.html', usuario=user, musicas=data)

@app.route('/adicionar', methods=['POST'])
def adicionar():
    termo = request.form['termo']
    user = request.form['usuario']
    resultado = buscar_video_youtube(termo)
    if not resultado:
        return "Erro: Nenhum vídeo encontrado."
    thumb_path = os.path.join(IMAGE_FOLDER, f"{resultado['id']}.jpg")
    try:
        img_data = requests.get(resultado['thumbnail_url']).content
        with open(thumb_path, 'wb') as f:
            f.write(img_data)
    except:
        thumb_path = None
    musica = {
        "titulo": resultado['titulo'],
        "link": resultado['link'],
        "video_id": resultado['id'],
        "thumbnail_url": resultado['thumbnail_url'],
        "thumbnail_path": f"/thumb/{resultado['id']}.jpg"
    }
    data = load_user_data(user)
    data.insert(0, musica)
    save_user_data(user, data)
    return redirect(url_for('perfil') + f"?usuario={user}")

@app.route('/thumb/<filename>')
def thumb(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/excluir/<usuario>/<int:index>')
def excluir(usuario, index):
    data = load_user_data(usuario)
    if index >= len(data): return redirect(url_for('perfil') + f"?usuario={usuario}")
    musica = data.pop(index)
    if 'thumbnail_path' in musica and musica['thumbnail_path']:
        path = os.path.join(IMAGE_FOLDER, os.path.basename(musica['thumbnail_path']))
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                pass
    save_user_data(usuario, data)
    return redirect(url_for('perfil') + f"?usuario={usuario}")