from flask import Flask, render_template, request, make_response, redirect, url_for, session
from googletrans import Translator
import csv
from io import StringIO
from functools import wraps
import logging
from flask_sqlalchemy import SQLAlchemy
import firebase_admin
from firebase_admin import credentials, auth


app = Flask(__name__)
app.secret_key = 'adfasfasasdf'

# Firebase setup
cred = credentials.Certificate("D:/GitHub/Translator/translator-f9772-firebase-adminsdk-ybzox-3d49d5b518.json")
firebase_admin.initialize_app(cred)


# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///translator.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
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
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        email = session['user_email']
        subject = request.form['subject']
        message = request.form['message']
        feedback_entry = Feedback(email=email, subject=subject, message=message)
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
        data = request.get_json()  # Get the JSON data from the request
        email = data.get('email')
        password = data.get('password')
        id_token = data.get('idToken')

        if email and password:  # Make sure email and password are provided
            try:
                user = auth.get_user_by_email(email)  # Verify if user exists
                user_record = auth.verify_id_token(id_token)  # Firebase ID token verification
                session['user_id'] = user_record['uid']
                session['user_email'] = email
                # Debugging: Ensure that the session is set
                print(f"Logged in user: {session.get('user_email')}")
                return redirect(url_for('index'))  # Ensure correct redirect
            except Exception as e:
                return str(e)
        else:
            return "Missing email or password", 400  # Handle missing fields gracefully

    return render_template('login.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        phone = request.form['phone']

        # Validate input
        if password != confirm_password:
            return "Passwords do not match", 400

        try:
            # Register user with Firebase
            user = auth.create_user(
                email=email,
                password=password,
                display_name=name,
                phone_number=phone if phone else None
            )
            return redirect(url_for('login'))
        except Exception as e:
            return str(e), 400

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
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
            user = User.query.filter_by(email=session['user_email']).first()
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
    user = User.query.filter_by(email=session['user_email']).first()
    return render_template('history.html', history=user.history)

@app.route('/favorites')
@login_required
def show_favorites():
    user = User.query.filter_by(email=session['user_email']).first()
    return render_template('favorites.html', favorites=user.favorites)

@app.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.all()
    leaderboard_data = [{'email': user.email, 'points': len(user.history) + len(user.favorites)} for user in users]
    return render_template('leaderboard.html', users=leaderboard_data)

@app.route('/download_history')
@login_required
def download_history():
    user = User.query.filter_by(email=session['user_email']).first()
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
    user = User.query.filter_by(email=session['user_email']).first()
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
    user = User.query.filter_by(email=session['user_email']).first()
    new_favorite = Favorite(text=text, translation=translation, src=src, dest=dest, user=user)
    db.session.add(new_favorite)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/clear_favorites')
@login_required
def clear_favorites():
    user = User.query.filter_by(email=session['user_email']).first()
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


@app.route('/set_session', methods=['POST'])
def set_session():
    data = request.get_json()  # Get JSON data from the request body
    email = data.get('email')  # Access the email from the JSON payload
    session['user_email'] = email  # Set the session data
    return '', 204  # No content response, as we don't need to return anything



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
