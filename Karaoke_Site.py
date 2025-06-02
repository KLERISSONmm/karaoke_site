# app.py
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import os, json, re, urllib.parse
import requests
from pytubefix import YouTube

app = Flask(__name__)

DATA_FOLDER = "dados_karaoke"
MUSIC_FOLDER = os.path.join(DATA_FOLDER, "musicas")
IMAGE_FOLDER = os.path.join(DATA_FOLDER, "thumbnails")
os.makedirs(MUSIC_FOLDER, exist_ok=True)
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

def buscar_video_youtube(termo, max_results=1):
    query = urllib.parse.quote(termo)
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults={max_results}&q={query}+karaoke&key={YOUTUBE_API_KEY}"
    response = requests.get(url)
    data = response.json()
    resultados = []
    if 'items' in data:
        for item in data['items']:
            video_id = item['id']['videoId']
            titulo = item['snippet']['title']
            thumb_url = item['snippet']['thumbnails']['high']['url']
            resultados.append({
                'id': video_id,
                'titulo': titulo,
                'link': f"https://www.youtube.com/watch?v={video_id}",
                'thumbnail_url': thumb_url
            })
    return resultados

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

@app.route('/buscar', methods=['GET', 'POST'])
def buscar():
    user = request.args.get('usuario') or request.form.get('usuario')
    termo = request.form.get('termo') if request.method == 'POST' else ''
    resultados = buscar_video_youtube(termo, max_results=10) if termo else []
    return render_template('buscar.html', usuario=user, termo=termo, resultados=resultados)

@app.route('/adicionar_favorito', methods=['POST'])
def adicionar_favorito():
    user = request.form['usuario']
    titulo = request.form['titulo']
    link = request.form['link']
    thumb_url = request.form['thumbnail_url']
    video_id = request.form['video_id']

    thumb_path = os.path.join(IMAGE_FOLDER, f"{video_id}.jpg")
    try:
        img_data = requests.get(thumb_url).content
        with open(thumb_path, 'wb') as f:
            f.write(img_data)
    except:
        thumb_path = None

    musica = {
        "titulo": titulo,
        "link": link,
        "thumbnail_url": thumb_url,
        "thumbnail_path": f"/thumb/{video_id}.jpg"
    }

    data = load_user_data(user)
    data.append(musica)
    save_user_data(user, data)
    return redirect(url_for('perfil') + f"?usuario={user}")

@app.route('/adicionar', methods=['POST'])
def adicionar():
    termo = request.form['termo']
    user = request.form['usuario']

    resultados = buscar_video_youtube(termo, max_results=1)
    if not resultados:
        return "Erro: Nenhum vídeo encontrado."

    resultado = resultados[0]
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
        "thumbnail_url": resultado['thumbnail_url'],
        "thumbnail_path": f"/thumb/{resultado['id']}.jpg"
    }

    data = load_user_data(user)
    data.append(musica)
    save_user_data(user, data)
    return redirect(url_for('perfil') + f"?usuario={user}")

@app.route('/thumb/<filename>')
def thumb(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/video/<usuario>/<int:index>')
def video(usuario, index):
    data = load_user_data(usuario)
    if index >= len(data): return "Erro: índice inválido"
    url = data[index]['link']
    title = data[index]['titulo']

    filename = sanitize_filename(title) + ".mp4"
    filepath = os.path.join(MUSIC_FOLDER, filename)

    if not os.path.exists(filepath):
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if stream:
            stream.download(output_path=MUSIC_FOLDER, filename=filename)

    return send_from_directory(MUSIC_FOLDER, filename)

@app.route('/excluir/<usuario>/<int:index>')
def excluir(usuario, index):
    data = load_user_data(usuario)
    if index >= len(data): return redirect(url_for('perfil') + f"?usuario={usuario}")
    musica = data.pop(index)

    if 'thumbnail_path' in musica and musica['thumbnail_path']:
        path = os.path.join(IMAGE_FOLDER, os.path.basename(musica['thumbnail_path']))
        if os.path.exists(path): os.remove(path)

    filepath = os.path.join(MUSIC_FOLDER, sanitize_filename(musica['titulo']) + ".mp4")
    if os.path.exists(filepath): os.remove(filepath)

    save_user_data(usuario, data)
    return redirect(url_for('perfil') + f"?usuario={usuario}")

if __name__ == '__main__':
    app.run(debug=True)
