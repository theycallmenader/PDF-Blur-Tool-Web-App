from flask import Flask, render_template, request, send_file, jsonify
import os
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np
import uuid
import img2pdf

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
IMAGE_FOLDER = "pages"
OUTPUT_FOLDER = "output"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['IMAGE_FOLDER'] = IMAGE_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
    file.save(file_path)

    images = convert_from_path(file_path, dpi=300, fmt='png')
    image_files = []
    for i, img in enumerate(images):
        resized = img.resize((2480, 3508), Image.LANCZOS)
        image_name = f"{file_id}_page_{i+1}.png"
        image_path = os.path.join(app.config['IMAGE_FOLDER'], image_name)
        resized.save(image_path, "PNG")
        image_files.append(image_name)

    return jsonify({"images": image_files, "file_id": file_id})

@app.route('/images/<filename>')
def get_image(filename):
    return send_file(os.path.join(app.config['IMAGE_FOLDER'], filename))

@app.route('/blur', methods=['POST'])
def blur():
    data = request.json
    file_id = data.get('file_id')
    blur_data = data.get('blur_data', [])
    blurred_images = []

    for entry in blur_data:
        filename = entry['page']
        zones = entry['zones']
        path = os.path.join(app.config['IMAGE_FOLDER'], filename)
        image = cv2.imread(path)

        for zone in zones:
            y1, y2 = int(zone['y1']), int(zone['y2'])
            x1, x2 = int(zone['x1']), int(zone['x2'])
            roi = image[y1:y2, x1:x2]
            blurred = cv2.GaussianBlur(roi, (21, 21), 0)
            image[y1:y2, x1:x2] = blurred

        out_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        cv2.imwrite(out_path, image)
        blurred_images.append(out_path)

    output_pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{file_id}_blurred.pdf")
    with open(output_pdf_path, "wb") as f:
        f.write(img2pdf.convert(blurred_images))

    return send_file(output_pdf_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
