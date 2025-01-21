from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
from flask_session import Session
import requests
import firebase_admin
from firebase_admin import credentials, auth
from googletrans import Translator
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
import csv
from io import StringIO

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "adfasfasasdf"

# Flask-Session configuration
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Firebase setup
cred = credentials.Certificate("E:/TEAM EXCALIBUR/Translator/Translator/translator-f9772-firebase-adminsdk-ybzox-3d49d5b518.json")
firebase_admin.initialize_app(cred)

# Initialize Google Translator
translator = Translator()

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

# Redirect to login page if not logged in
def check_logged_in():
    if 'user_email' not in session:
        return redirect(url_for('login'))

@app.route('/home', methods=['GET', 'POST'])
def home():
    if check_logged_in():
        return check_logged_in()

    translation = ''
    detected_lang = ''
    error = ''
    suggestion = ''

    if request.method == 'POST':
        text_to_translate = request.form['text']
        src_lang = request.form['src_lang']
        dest_lang = request.form['dest_lang']

        try:
            history = session.get('history', [])
            suggestion = suggest_translation(text_to_translate, history)
            if not suggestion:
                if src_lang == 'auto':
                    detected_lang = translator.detect(text_to_translate).lang
                    src_lang = detected_lang
                translated = translator.translate(text_to_translate, src=src_lang, dest=dest_lang)
                translation = translated.text
                history.append({
                    'text': text_to_translate,
                    'translation': translation,
                    'src': src_lang,
                    'dest': dest_lang
                })
                session['history'] = history
                logging.info(f"Translated from {src_lang} to {dest_lang}: {text_to_translate} -> {translation}")
        except Exception as e:
            error = str(e)
            logging.error(f"Error translating from {src_lang} to {dest_lang}: {text_to_translate} - {error}")

    return render_template('home.html', translation=translation, detected_lang=detected_lang, error=error, suggestion=suggestion)

@app.route('/', methods=['GET', 'POST'])
def index():
    # Check if user is logged in
    if check_logged_in():
        return check_logged_in()

    translation = ''
    detected_lang = ''
    error = ''
    suggestion = ''
    if request.method == 'POST':
        text_to_translate = request.form['text']
        src_lang = request.form['src_lang']
        dest_lang = request.form['dest_lang']
        try:
            history = session.get('history', [])
            suggestion = suggest_translation(text_to_translate, history)
            if not suggestion:
                if src_lang == 'auto':
                    detected_lang = translator.detect(text_to_translate).lang
                    src_lang = detected_lang
                translated = translator.translate(text_to_translate, src=src_lang, dest=dest_lang)
                translation = translated.text
                history.append({
                    'text': text_to_translate,
                    'translation': translation,
                    'src': src_lang,
                    'dest': dest_lang
                })
                session['history'] = history
                logging.info(f"Translated from {src_lang} to {dest_lang}: {text_to_translate} -> {translation}")
        except Exception as e:
            error = str(e)
            logging.error(f"Error translating from {src_lang} to {dest_lang}: {text_to_translate} - {error}")
    return render_template('home.html', translation=translation, detected_lang=detected_lang, error=error, suggestion=suggestion)

@app.route('/translate', methods=['POST'])
def translate():
    if check_logged_in():
        return check_logged_in()

    text = request.form['text']
    src_lang = request.form['src_lang']
    dest_lang = request.form['dest_lang']
    result = translator.translate(text, src=src_lang, dest=dest_lang)
    history = session.get('history', [])
    history.append({
        'src': src_lang,
        'dest': dest_lang,
        'text': text,
        'translation': result.text
    })
    session['history'] = history
    session['translation'] = result.text
    return redirect(url_for('home'))

@app.route('/add_favorite', methods=['POST'])
def add_favorite():
    if check_logged_in():
        return check_logged_in()

    favorite = {
        'text': request.form['text'],
        'translation': request.form['translation'],
        'src': request.form['src'],
        'dest': request.form['dest']
    }
    favorites = session.get('favorites', [])
    favorites.append(favorite)
    session['favorites'] = favorites
    return redirect(url_for('home'))

@app.route('/show_history')
def show_history():
    if check_logged_in():
        return check_logged_in()
    return render_template('history.html', history=session.get('history', []))

@app.route('/clear_history')
def clear_history():
    session['history'] = []
    return redirect(url_for('show_history'))

@app.route('/show_favorites')
def show_favorites():
    if check_logged_in():
        return check_logged_in()
    return render_template('favorites.html', favorites=session.get('favorites', []))

@app.route('/clear_favorites')
def clear_favorites():
    session['favorites'] = []
    return redirect(url_for('show_favorites'))

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        feedback = request.form['feedback']
        logging.info(f"Feedback received: {feedback}")
        return redirect(url_for('home'))
    return render_template('feedback.html')

@app.route('/leaderboard')
def leaderboard():
    # Placeholder leaderboard logic
    return "Leaderboard page (not implemented yet)"

@app.route('/download_history')
def download_history():
    history = session.get('history', [])
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Source Language', 'Destination Language', 'Original Text', 'Translation'])
    for item in history:
        writer.writerow([item['src'], item['dest'], item['text'], item['translation']])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=translation_history.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/toggle_dark_mode', methods=['POST'])
def toggle_dark_mode():
    data = request.get_json()
    dark_mode = data.get('dark_mode', False)
    session['dark_mode'] = dark_mode
    return '', 204

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.json['email']
        id_token = request.json['idToken']
        try:
            decoded_token = auth.verify_id_token(id_token)
            session['user_email'] = decoded_token['email']
            return jsonify({"message": "Login successful!"}), 200  # Send a success message back to frontend
        except Exception as e:
            return jsonify({"error": str(e)}), 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
