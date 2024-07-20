from flask import Flask, render_template, request, make_response, redirect, url_for, session
from googletrans import Translator
import csv
from io import StringIO
from functools import wraps
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'
translator = Translator()
history = []
favorites = []

# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

# Helper function to suggest translations
def suggest_translation(text, history):
    if not history:
        return None
    texts = [item['text'] for item in history]
    texts.append(text)
    vectorizer = CountVectorizer().fit_transform(texts)
    vectors = vectorizer.toarray()
    cosine_matrix = cosine_similarity(vectors)
    similar_index = cosine_matrix[-1][:-1].argmax()
    return history[similar_index]['translation']

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        session['username'] = username
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    translation = ''
    detected_lang = ''
    error = ''
    suggestion = ''
    if request.method == 'POST':
        text_to_translate = request.form['text']
        src_lang = request.form['src_lang']
        dest_lang = request.form['dest_lang']
        try:
            suggestion = suggest_translation(text_to_translate, history)
            if not suggestion:
                if src_lang == 'auto':
                    detected_lang = translator.detect(text_to_translate).lang
                    src_lang = detected_lang
                translated = translator.translate(text_to_translate, src=src_lang, dest=dest_lang)
                translation = translated.text
                history.append({'text': text_to_translate, 'translation': translation, 'src': src_lang, 'dest': dest_lang})
                logging.info(f"Translated from {src_lang} to {dest_lang}: {text_to_translate} -> {translation}")
        except Exception as e:
            error = str(e)
            logging.error(f"Error translating from {src_lang} to {dest_lang}: {text_to_translate} - {error}")
    return render_template('index.html', translation=translation, detected_lang=detected_lang, error=error, suggestion=suggestion)

@app.route('/history')
@login_required
def show_history():
    return render_template('history.html', history=history)

@app.route('/favorites')
@login_required
def show_favorites():
    return render_template('favorites.html', favorites=favorites)

@app.route('/leaderboard')
@login_required
def leaderboard():
    # Removed database interaction
    users = [{'username': 'user1', 'points': 10}, {'username': 'user2', 'points': 5}]
    return render_template('leaderboard.html', users=users)

@app.route('/download_history')
@login_required
def download_history():
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Source Language', 'Destination Language', 'Original Text', 'Translation'])
    for item in history:
        writer.writerow([item['src'], item['dest'], item['text'], item['translation']])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=translation_history.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/clear_history')
@login_required 
def clear_history():
    global history
    history = []
    return redirect(url_for('show_history'))

@app.route('/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    text = request.form['text']
    translation = request.form['translation']
    src = request.form['src']
    dest = request.form['dest']
    favorites.append({'text': text, 'translation': translation, 'src': src, 'dest': dest})
    return redirect(url_for('index'))

@app.route('/clear_favorites')
@login_required
def clear_favorites():
    global favorites
    favorites = []
    return redirect(url_for('show_favorites'))

if __name__ == '__main__':
    app.run(debug=True)
