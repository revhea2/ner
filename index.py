import json
import os
import pdftotext
import spacy
import re
from flask import Flask, render_template, request, redirect, abort
from flask.helpers import send_from_directory
from werkzeug.utils import secure_filename
from nltk.tokenize import word_tokenize

app = Flask(__name__)

UPLOAD_FOLDER = app.root_path + ("\\uploads")
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
TOKENS_DIRECTORY = 'tokens.json'


def allowed_file(filename):
    name, extension = filename.split('.')
    return extension in ALLOWED_EXTENSIONS


def clean_text(text):
    cleaned_text = re.sub(r'(\s+\d\s+)|([\r\n]+)|(\s+)', ' ', text)
    return cleaned_text


def update_tokens_json(new_data):
    with open(TOKENS_DIRECTORY) as f:
        data = json.load(f)
    data.update(new_data)
    with open(TOKENS_DIRECTORY, 'w') as f:
        json.dump(data, f)


def add_to_token(text_from_pdf, filename):
    nlp = spacy.load("en_core_web_sm")
    cleaned_text = clean_text(text_from_pdf)
    doc = nlp(cleaned_text)
    entities = []
    for ent in doc.ents:
        entities.append(str(ent))
    data = {filename: {
        "entities": entities
    }}
    update_tokens_json(data)


def search_files(search_requests):
    regex = ""
    for search_request in search_requests:
        regex += f"({search_request.lower()})|"

    if len(regex) > 0:
        regex = regex[0:-1]

    with open(TOKENS_DIRECTORY) as f:
        data = json.load(f)
    files = []
    id_ = 1
    for article in data:
        for key, entities in data[article].items():
            for entity in entities:
                if re.match(rf"{regex}", entity.lower()):
                    files.append([id_, re.sub("_", " ", article.split('.')[0]), article])
                    id_ += 1
                    break
    return files


@app.route('/', methods=['GET', 'POST'])
def index():
    text_from_pdf = None
    if request.method == 'POST':
        if request.method == "POST":
            if 'file' not in request.files:
                return redirect(request.url)
            file = request.files['file']
            if file.filename == "":
                return redirect(request.url)

            if not allowed_file(file.filename):
                return redirect(request.url)

            if file:
                filename = secure_filename(file.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(upload_path)
                with open(upload_path, 'rb') as f:
                    pdf = pdftotext.PDF(f, "secret")
                    text_from_pdf = "\n".join(pdf)
                    add_to_token(text_from_pdf, filename)

        return render_template('index.html', text_from_pdf=text_from_pdf)
    return render_template('index.html')


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_req = request.form['search']
        search_request = word_tokenize(search_req)
        files = search_files(search_request)
        return render_template('search.html', files=files, search_req=search_req)
    return render_template('search.html', gets=True, )


@app.route('/get_file/<filename>')
def fetch_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], path=filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)


if __name__ == '__main__':
    app.run(debug=True)
    # app.run(debug=True, host='0.0.0.0')
