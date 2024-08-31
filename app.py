from flask import Flask, render_template, request, make_response, redirect, url_for, session
from googletrans import Translator
import csv
from io import StringIO
from functools import wraps
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///translator.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    history = db.relationship('History', backref='user', lazy=True)
    favorites = db.relationship('Favorite', backref='user', lazy=True)

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    translation = db.Column(db.Text, nullable=False)
    src = db.Column(db.String(50), nullable=False)
    dest = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    translation = db.Column(db.Text, nullable=False)
    src = db.Column(db.String(50), nullable=False)
    dest = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Feedback Model
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)

translator = Translator()

# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

# Helper function to suggest translations
def suggest_translation(text, history):
    if not history:
        return None
    texts = [item.text for item in history]
    texts.append(text)
    vectorizer = CountVectorizer().fit_transform(texts)
    vectors = vectorizer.toarray()
    cosine_matrix = cosine_similarity(vectors)
    similar_index = cosine_matrix[-1][:-1].argmax()
    return history[similar_index].translation

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        username = session['username']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']
        feedback_entry = Feedback(username=username, email=email, subject=subject, message=message)
        db.session.add(feedback_entry)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('feedback.html')

@app.route('/view_feedback')
@login_required
def view_feedback():
    feedbacks = Feedback.query.all()
    return render_template('view_feedback.html', feedbacks=feedbacks)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
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
            user = User.query.filter_by(username=session['username']).first()
            suggestion = suggest_translation(text_to_translate, user.history)
            if not suggestion:
                if src_lang == 'auto':
                    detected_lang = translator.detect(text_to_translate).lang
                    src_lang = detected_lang
                translated = translator.translate(text_to_translate, src=src_lang, dest=dest_lang)
                translation = translated.text
                new_history = History(text=text_to_translate, translation=translation, src=src_lang, dest=dest_lang, user=user)
                db.session.add(new_history)
                db.session.commit()
                logging.info(f"Translated from {src_lang} to {dest_lang}: {text_to_translate} -> {translation}")
        except Exception as e:
            error = str(e)
            logging.error(f"Error translating from {src_lang} to {dest_lang}: {text_to_translate} - {error}")
    return render_template('index.html', translation=translation, detected_lang=detected_lang, error=error, suggestion=suggestion)

@app.route('/history')
@login_required
def show_history():
    user = User.query.filter_by(username=session['username']).first()
    return render_template('history.html', history=user.history)

@app.route('/favorites')
@login_required
def show_favorites():
    user = User.query.filter_by(username=session['username']).first()
    return render_template('favorites.html', favorites=user.favorites)

@app.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.all()
    leaderboard_data = [{'username': user.username, 'points': len(user.history) + len(user.favorites)} for user in users]
    return render_template('leaderboard.html', users=leaderboard_data)

@app.route('/download_history')
@login_required
def download_history():
    user = User.query.filter_by(username=session['username']).first()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Source Language', 'Destination Language', 'Original Text', 'Translation'])
    for item in user.history:
        writer.writerow([item.src, item.dest, item.text, item.translation])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=translation_history.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/clear_history')
@login_required
def clear_history():
    user = User.query.filter_by(username=session['username']).first()
    for item in user.history:
        db.session.delete(item)
    db.session.commit()
    return redirect(url_for('show_history'))

@app.route('/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    text = request.form['text']
    translation = request.form['translation']
    src = request.form['src']
    dest = request.form['dest']
    user = User.query.filter_by(username=session['username']).first()
    new_favorite = Favorite(text=text, translation=translation, src=src, dest=dest, user=user)
    db.session.add(new_favorite)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/clear_favorites')
@login_required
def clear_favorites():
    user = User.query.filter_by(username=session['username']).first()
    for item in user.favorites:
        db.session.delete(item)
    db.session.commit()
    return redirect(url_for('show_favorites'))

@app.route('/toggle_dark_mode', methods=['POST'])
@login_required
def toggle_dark_mode():
    data = request.get_json()
    dark_mode = data.get('dark_mode', False)
    session['dark_mode'] = dark_mode
    return '', 204



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
