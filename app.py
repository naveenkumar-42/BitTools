from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session
import requests
import firebase_admin
from firebase_admin import credentials, auth
from googletrans import Translator

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "adfasfasasdf"

# Flask-Session configuration
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Firebase configuration
# Firebase setup
cred = credentials.Certificate("D:/GitHub/Translator/translator-f9772-firebase-adminsdk-ybzox-3d49d5b518.json")
firebase_admin.initialize_app(cred)
# Initialize Google Translator
translator = Translator()

# In-memory storage for user history and favorites
user_data = {
    "history": [],
    "favorites": []
}

@app.route('/home')
def home():
    return render_template('home.html')  # Ensure you have a `home.html` template in your `templates` folder


# Routes
@app.route('/')
def index():
    return render_template('login.html', history=session.get('history', []), translation=session.get('translation'),
                           suggestion=session.get('suggestion'))

@app.route('/translate', methods=['POST'])
def translate():
    text = request.form['text']
    src_lang = request.form['src_lang']
    dest_lang = request.form['dest_lang']

    # Perform translation
    result = translator.translate(text, src=src_lang, dest=dest_lang)
    session['translation'] = result.text
    session['history'] = session.get('history', [])
    session['history'].append({
        'src': src_lang,
        'dest': dest_lang,
        'text': text,
        'translation': result.text
    })

    return redirect(url_for('index'))

@app.route('/add_favorite', methods=['POST'])
def add_favorite():
    favorite = {
        'text': request.form['text'],
        'translation': request.form['translation'],
        'src': request.form['src'],
        'dest': request.form['dest']
    }
    session['favorites'] = session.get('favorites', [])
    session['favorites'].append(favorite)
    return redirect(url_for('index'))

@app.route('/show_history')
def show_history():
    return render_template('history.html', history=session.get('history', []))

@app.route('/show_favorites')
def show_favorites():
    return render_template('favorites.html', favorites=session.get('favorites', []))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.json['email']
        id_token = request.json['idToken']

        try:
            decoded_token = auth.verify_id_token(id_token)
            session['username'] = decoded_token['email']
            return jsonify({"message": "Login successful!"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 401

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        feedback = request.form['feedback']
        # Save feedback (you can store this in a database)
        return redirect(url_for('index'))

    return render_template('feedback.html')

@app.route('/view_feedback')
def view_feedback():
    # Render feedback from the database if implemented
    return "Feedback page (not implemented yet)"

@app.route('/leaderboard')
def leaderboard():
    # Leaderboard logic (not implemented yet)
    return "Leaderboard page (not implemented yet)"

@app.route('/set_session', methods=['POST'])
def set_session():
    data = request.get_json()
    session['username'] = data['email']
    return jsonify({"message": "Session set!"}), 200

if __name__ == '__main__':
    app.run(debug=True)