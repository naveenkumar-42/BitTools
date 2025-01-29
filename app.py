from flask import Flask,flash, render_template, request, redirect, url_for, session, jsonify, make_response,send_file
from flask_session import Session
import random
import requests
import firebase_admin
from firebase_admin import credentials, auth
from googletrans import Translator
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
import csv
from io import StringIO
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from docx import Document
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
from fpdf import FPDF
import os
import img2pdf
import openpyxl
import io
import zipfile
from io import BytesIO
import shutil
import tempfile
import os
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from docx2pdf import convert
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import openpyxl
import fitz  # PyMuPDF


# Initialize Flask app
app = Flask(__name__)
app.secret_key = "adfasfasasdf"

# Specify upload folder (relative path)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'jpg', 'jpeg', 'png', 'xlsx', 'txt', 'html'}

# Flask-Session configuration
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Firebase setup
cred = credentials.Certificate("translator-f9772-firebase-adminsdk-ybzox-3d49d5b518.json")
firebase_admin.initialize_app(cred)

# Initialize Google Translator
translator = Translator()

# Paths for the text files containing different difficulty sentences
SENTENCES_DIR = 'static/sentences'

# Function to read paragraphs from a file
def load_paragraphs(file_name):
    file_path = os.path.join(SENTENCES_DIR, file_name)
    with open(file_path, 'r', encoding="utf-8") as file:
        paragraphs = file.read().strip().split("\n\n")  # Split by double newlines
    return paragraphs

# Load paragraphs for each difficulty level
paragraphs = {
    "easy": load_paragraphs("easy.txt"),
    "medium": load_paragraphs("medium.txt"),
    "hard": load_paragraphs("hard.txt")
}

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

# Helper function to check file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Redirect to login page if not logged in
def check_logged_in():
    if 'user_email' not in session:
        return redirect(url_for('login'))

# @app.route('/home', methods=['GET', 'POST'])
# def home():
#     if check_logged_in():
#         return check_logged_in()

#     translation = ''
#     detected_lang = ''
#     error = ''
#     suggestion = ''

#     if request.method == 'POST':
#         text_to_translate = request.form.get('text')  # Use .get() to avoid KeyError
#         src_lang = request.form.get('src_lang', 'auto')  # Default to 'auto' if not provided
#         dest_lang = request.form.get('dest_lang')

#         try:
#             # Ensure 'text' and 'dest_lang' are provided
#             if not text_to_translate or not dest_lang:
#                 raise ValueError("Missing required fields: text or destination language")

#             history = session.get('history', [])
#             suggestion = suggest_translation(text_to_translate, history)
#             if not suggestion:
#                 if src_lang == 'auto':
#                     detected_lang = translator.detect(text_to_translate).lang
#                     src_lang = detected_lang
#                 translated = translator.translate(text_to_translate, src=src_lang, dest=dest_lang)
#                 translation = translated.text
#                 history.append({
#                     'text': text_to_translate,
#                     'translation': translation,
#                     'src': src_lang,
#                     'dest': dest_lang
#                 })
#                 session['history'] = history
#                 logging.info(f"Translated from {src_lang} to {dest_lang}: {text_to_translate} -> {translation}")
#         except Exception as e:
#             error = str(e)
#             logging.error(f"Error translating from {src_lang} to {dest_lang}: {text_to_translate} - {error}")

#     return render_template('home.html', translation=translation, detected_lang=detected_lang, error=error, suggestion=suggestion)


# @app.route('/', methods=['GET', 'POST'])
# def index():
#     # Check if user is logged in
#     if check_logged_in():
#         return check_logged_in()

#     translation = ''
#     detected_lang = ''
#     error = ''
#     suggestion = ''
#     if request.method == 'POST':
#         text_to_translate = request.form['text']
#         src_lang = request.form['src_lang']
#         dest_lang = request.form['dest_lang']
#         try:
#             history = session.get('history', [])
#             suggestion = suggest_translation(text_to_translate, history)
#             if not suggestion:
#                 if src_lang == 'auto':
#                     detected_lang = translator.detect(text_to_translate).lang
#                     src_lang = detected_lang
#                 translated = translator.translate(text_to_translate, src=src_lang, dest=dest_lang)
#                 translation = translated.text
#                 history.append({
#                     'text': text_to_translate,
#                     'translation': translation,
#                     'src': src_lang,
#                     'dest': dest_lang
#                 })
#                 session['history'] = history
#                 logging.info(f"Translated from {src_lang} to {dest_lang}: {text_to_translate} -> {translation}")
#         except Exception as e:
#             error = str(e)
#             logging.error(f"Error translating from {src_lang} to {dest_lang}: {text_to_translate} - {error}")
#     return render_template('home.html', translation=translation, detected_lang=detected_lang, error=error, suggestion=suggestion)

# @app.route('/translate', methods=['POST'])
# def translate():
#     if check_logged_in():
#         return check_logged_in()

#     text = request.form['text']
#     src_lang = request.form['src_lang']
#     dest_lang = request.form['dest_lang']
#     result = translator.translate(text, src=src_lang, dest=dest_lang)
#     history = session.get('history', [])
#     history.append({
#         'src': src_lang,
#         'dest': dest_lang,
#         'text': text,
#         'translation': result.text
#     })
#     session['history'] = history
#     session['translation'] = result.text
#     return redirect(url_for('home'))



# History and favorites (in-memory for now)
history = []
favorites = []

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/translator', methods=['GET', 'POST'])
def translator():
    translation = None
    suggestion = None

    if request.method == 'POST':
        src_lang = request.form.get('src_lang')
        dest_lang = request.form.get('dest_lang')
        text = request.form.get('text')

        # Using googletrans library to translate
        translator = Translator()
        translated = translator.translate(text, src=src_lang, dest=dest_lang)

        # Saving history
        history.append({
            'src': src_lang,
            'dest': dest_lang,
            'text': text,
            'translation': translated.text
        })

        translation = translated.text

        # If you want to give suggestions (for example, use the same translation if empty)
        if not translation:
            suggestion = "Suggested translation goes here."

    return render_template('translator.html', translation=translation, suggestion=suggestion, history=history)


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
    flash('Added to favorites!')
    return redirect(url_for('translator'))


@app.route('/favorites')
def favorites():
    if check_logged_in():
        return check_logged_in()

    favorites = session.get('favorites', [])
    return render_template('favorites.html', favorites=favorites)

@app.route('/clear_favorites', methods=['POST'])
def clear_favorites():
    if 'favorites' in session:
        session.pop('favorites')  # Remove the favorites from the session
        flash('Favorites cleared successfully!', 'success')
    else:
        flash('No favorites to clear!', 'info')
    return redirect(url_for('favorites'))


@app.route('/view_history')
def view_history():
    # Render the history page with the current history list
    return render_template('view_history.html', history=history)

@app.route('/clear_history', methods=['POST'])
def clear_history():
    global history
    history = []  # Clear the history list
    flash('Translation history cleared successfully!', 'success')
    return redirect(url_for('view_history'))


@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        feedback = request.form['feedback']
        logging.info(f"Feedback received: {feedback}")
        return redirect(url_for('home'))
    return render_template('feedback.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm-password']

        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match.')

        try:
            # Create a Firebase user
            user = auth.create_user(
                email=email,
                password=password,
                display_name=name,
                phone_number=phone
            )

            # Send a Thank You email
            send_thank_you_email(email, name)
            
            return redirect(url_for('login'))  # Redirect to login page after successful registration
        except Exception as e:
            return render_template('register.html', error=str(e))

    return render_template('register.html')


def send_thank_you_email(user_email, user_name):
    # Email credentials
    sender_email = "bittranslator2@gmail.com"
    sender_password = "rwvnocanknpbxgyb"  # Use App Password here if 2FA is enabled

    # Email content
    subject = "Thank You for Registering!"
    body = f"Hello {user_name},\n\nThank you for registering on our platform. We're excited to have you on board!\n\nBest regards,\nYour App Team"

    # Setting up the MIME
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = user_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    try:
        # Sending the email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            text = message.as_string()
            server.sendmail(sender_email, user_email, text)
            print("Thank you email sent successfully.")
    except smtplib.SMTPAuthenticationError as e:
        print(f"Authentication Error: {e}")
    except smtplib.SMTPConnectError as e:
        print(f"Connection Error: {e}")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")


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

@app.route('/convert_pdf', methods=['GET', 'POST'])
def convert_pdf():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return render_template('convert_pdf.html', error="No file uploaded.")
        
        pdf_file = request.files['pdf_file']
        if pdf_file.filename == '':
            return render_template('convert_pdf.html', error="No file selected.")
        
        try:
            # Save uploaded PDF securely
            filename = secure_filename(pdf_file.filename)
            pdf_path = f"{app.config['UPLOAD_FOLDER']}/{filename}"
            pdf_file.save(pdf_path)

            # Convert PDF to Word
            reader = PdfReader(pdf_path)
            doc = Document()

            for page in reader.pages:
                doc.add_paragraph(page.extract_text())

            # Save the Word file in the same folder
            word_filename = filename.rsplit('.', 1)[0] + '.docx'
            word_path = f"{app.config['UPLOAD_FOLDER']}/{word_filename}"
            doc.save(word_path)

            # Serve the Word file for download
            return send_file(word_path, as_attachment=True)

        except Exception as e:
            return render_template('convert_pdf.html', error=f"Error converting PDF: {str(e)}")
    
    return render_template('convert_pdf.html')

# Define route
@app.route('/convert_word_to_pdf', methods=['GET', 'POST'])
def convert_word_to_pdf():
    if request.method == 'POST':
        if 'word_file' not in request.files:
            return render_template('convert_word_to_pdf.html', error="No file uploaded.")
        
        word_file = request.files['word_file']
        if word_file.filename == '':
            return render_template('convert_word_to_pdf.html', error="No file selected.")
        
        try:
            filename = secure_filename(word_file.filename)
            word_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            word_file.save(word_path)
            
            # Convert Word document to PDF
            pdf_path = word_path.rsplit('.', 1)[0] + '.pdf'
            convert(word_path, pdf_path)

            return send_file(pdf_path, as_attachment=True)
        except Exception as e:
            return render_template('convert_word_to_pdf.html', error=f"Error: {str(e)}")
    
    return render_template('convert_word_to_pdf.html')


@app.route('/convert_image_to_pdf', methods=['GET', 'POST'])
def convert_image_to_pdf():
    if request.method == 'POST':
        if 'image_files' not in request.files:
            return render_template('convert_image_to_pdf.html', error="No file uploaded.")
        
        image_files = request.files.getlist('image_files')
        image_paths = []
        for file in image_files:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(image_path)
                image_paths.append(image_path)
        
        try:
            # Convert Images to PDF
            images = [Image.open(path) for path in image_paths]
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'output.pdf')
            images[0].save(pdf_path, save_all=True, append_images=images[1:])
            
            # Clean up images after conversion
            for path in image_paths:
                os.remove(path)

            # Return PDF file for download
            return send_file(pdf_path, as_attachment=True, download_name="converted_images.pdf")

        except Exception as e:
            return render_template('convert_image_to_pdf.html', error=f"Error: {str(e)}")
    
    return render_template('convert_image_to_pdf.html')

# Convert Excel to PDF

@app.route('/convert_excel_to_pdf', methods=['GET', 'POST'])
def convert_excel_to_pdf():
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            return render_template('convert_excel_to_pdf.html', error="No file uploaded.")
        
        excel_file = request.files['excel_file']
        if excel_file.filename == '':
            return render_template('convert_excel_to_pdf.html', error="No file selected.")
        
        try:
            filename = secure_filename(excel_file.filename)
            excel_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            excel_file.save(excel_path)
            
            # Convert Excel to PDF using ReportLab
            wb = openpyxl.load_workbook(excel_path)
            sheet = wb.active
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.rsplit('.', 1)[0] + '.pdf')
            c = canvas.Canvas(pdf_path, pagesize=letter)

            y_position = 750  # Starting Y position for writing to the PDF
            for row in sheet.iter_rows():
                row_text = ' '.join([str(cell.value) for cell in row])
                c.drawString(50, y_position, row_text)
                y_position -= 15  # Move to the next line
                if y_position < 50:  # Add a new page if text overflows
                    c.showPage()
                    y_position = 750

            c.save()

            return send_file(pdf_path, as_attachment=True)
        except Exception as e:
            return render_template('convert_excel_to_pdf.html', error=f"Error: {str(e)}")
    
    return render_template('convert_excel_to_pdf.html')

# Route for PDF compression
@app.route('/compress_pdf', methods=['GET', 'POST'])
def compress_pdf():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'No file uploaded.'})
        
        pdf_file = request.files['pdf_file']
        if pdf_file.filename == '':
            return jsonify({'error': 'No file selected.'})
        
        filename = secure_filename(pdf_file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        pdf_file.save(pdf_path)

        # Compress PDF
        original_size = os.path.getsize(pdf_path)
        input_pdf = PdfReader(pdf_path)
        output_pdf = PdfWriter()

        for page in input_pdf.pages:
            output_pdf.add_page(page)

        compressed_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'compressed_' + filename)
        with open(compressed_pdf_path, 'wb') as f:
            output_pdf.write(f)

        compressed_size = os.path.getsize(compressed_pdf_path)

        return jsonify({
            'original_size': original_size / 1024,  # KB
            'compressed_size': compressed_size / 1024,  # KB
            'compressed_filename': 'compressed_' + filename
        })

    return render_template('compress_pdf.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

# Convert PDF to Image
@app.route('/pdf_to_image', methods=['GET', 'POST'])
def pdf_to_image():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return render_template('pdf_to_image.html', error="No file uploaded.")
        
        pdf_file = request.files['pdf_file']
        if pdf_file.filename == '':
            return render_template('pdf_to_image.html', error="No file selected.")
        
        try:
            filename = secure_filename(pdf_file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(pdf_path)
            
            # Open the PDF with PyMuPDF (fitz)
            doc = fitz.open(pdf_path)
            image_paths = []
            for i in range(len(doc)):
                # Get the page as a pixmap (image)
                page = doc.load_page(i)
                pix = page.get_pixmap()
                img_path = os.path.join(app.config['UPLOAD_FOLDER'], f"page_{i+1}.png")
                pix.save(img_path)
                image_paths.append(img_path)
            
            # Return the first image for download (you can modify to return all images)
            return send_file(image_paths[0], as_attachment=True)
        except Exception as e:
            return render_template('pdf_to_image.html', error=f"Error: {str(e)}")
    
    return render_template('pdf_to_image.html')

# Merge PDFs
@app.route('/merge_pdfs', methods=['GET', 'POST'])
def merge_pdfs():
    if request.method == 'POST':
        if 'pdf_files' not in request.files:
            return render_template('merge_pdfs.html', error="No file uploaded.")
        
        pdf_files = request.files.getlist('pdf_files')
        pdf_paths = []
        for file in pdf_files:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(pdf_path)
                pdf_paths.append(pdf_path)
        
        try:
            # Merge PDFs
            pdf_writer = PdfWriter()
            for path in pdf_paths:
                pdf_reader = PdfReader(path)
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
            
            merged_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'merged.pdf')
            with open(merged_pdf_path, 'wb') as f:
                pdf_writer.write(f)

            # Clean up individual PDF files
            for path in pdf_paths:
                os.remove(path)
            
            return send_file(merged_pdf_path, as_attachment=True)
        except Exception as e:
            return render_template('merge_pdfs.html', error=f"Error: {str(e)}")
    
    return render_template('merge_pdfs.html')

# Function to parse page ranges
def parse_page_range(page_str):
    pages = set()
    for part in page_str.split(','):
        if '-' in part:
            start, end = part.split('-')
            pages.update(range(int(start), int(end) + 1))  # Add pages in the range
        else:
            pages.add(int(part))
    return sorted(pages)

# Split PDF
@app.route('/split_pdf', methods=['GET', 'POST'])
def split_pdf():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return render_template('split_pdf.html', error="No file uploaded.")
        
        pdf_file = request.files['pdf_file']
        if pdf_file.filename == '':
            return render_template('split_pdf.html', error="No file selected.")
        
        try:
            filename = secure_filename(pdf_file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(pdf_path)
            
            # Parse pages or ranges entered by the user
            page_str = request.form['pages']
            page_numbers = parse_page_range(page_str)
            
            # Read the PDF
            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            for page_num in page_numbers:
                if 1 <= page_num <= len(reader.pages):
                    writer.add_page(reader.pages[page_num - 1])  # Adjust for 0-based index

            split_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'split.pdf')
            with open(split_pdf_path, 'wb') as f:
                writer.write(f)

            return send_file(split_pdf_path, as_attachment=True)
        
        except Exception as e:
            return render_template('split_pdf.html', error=f"Error: {str(e)}")
    
    return render_template('split_pdf.html')


@app.route('/game/<difficulty>')
def game(difficulty):
    if difficulty not in paragraphs:
        return "Invalid difficulty", 404
    paragraph = random.choice(paragraphs[difficulty]).strip()
    return render_template('typing.html', paragraph=paragraph, difficulty=difficulty)

@app.route('/calculate_result/<string:user_input>/<int:start_time>/<int:end_time>/<difficulty>')
def calculate_result(user_input, start_time, end_time, difficulty):
    time_taken = (end_time - start_time) / 1000
    words_typed_list = user_input.strip().split()
    paragraph = random.choice(paragraphs[difficulty]).strip()
    correct_paragraph_words = paragraph.split()

    correct_count = sum(1 for i in range(min(len(words_typed_list), len(correct_paragraph_words))) if words_typed_list[i] == correct_paragraph_words[i])
    total_words_typed = len(words_typed_list)

    wpm = (total_words_typed / time_taken) * 60 if time_taken > 0 else 0
    accuracy = (correct_count / len(correct_paragraph_words)) * 100 if correct_paragraph_words else 0

    return jsonify({
        'wpm': round(wpm, 2),
        'accuracy': round(accuracy, 2),
        'time_taken': round(time_taken, 2),
        'words_typed': total_words_typed,
        'correct_words': correct_count
    })


if __name__ == '__main__':
    app.run(debug=True)
