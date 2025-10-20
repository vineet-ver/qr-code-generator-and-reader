from flask import Flask, render_template, request, send_file, redirect, url_for, flash, make_response
import qrcode
from io import BytesIO
from PIL import Image
import cv2
import numpy as np

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    PYZBAR_AVAILABLE = True
except Exception:
    PYZBAR_AVAILABLE = False

app = Flask(__name__)
app.secret_key = "qr-secret-key"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    content = request.form.get('content', '').strip()
    if not content:
        flash('Please provide content for the QR code.')
        return redirect(url_for('index'))

    try:
        box_size = int(request.form.get('box_size') or 10)
    except ValueError:
        box_size = 10
    try:
        border = int(request.form.get('border') or 4)
    except ValueError:
        border = 4

    fg = request.form.get('fg_color') or '#000000'
    bg = request.form.get('bg_color') or '#ffffff'

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=box_size, border=border)
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fg, back_color=bg).convert('RGB')

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    output = request.form.get('output') or 'view'
    if output == 'download':
        return send_file(buf, mimetype='image/png', as_attachment=True, download_name='qrcode.png')
    else:
        response = make_response(buf.read())
        response.headers.set('Content-Type', 'image/png')
        return response

def decode_with_pyzbar(pil_image):
    decoded = []
    if not PYZBAR_AVAILABLE:
        return decoded
    try:
        res = pyzbar_decode(pil_image)
        for r in res:
            decoded.append(r.data.decode('utf-8', errors='ignore'))
    except Exception:
        pass
    return decoded

def decode_with_opencv(pil_image):
    decoded = []
    try:
        open_cv_image = np.array(pil_image.convert('RGB'))
        open_cv_image = open_cv_image[:, :, ::-1].copy()
        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecodeMulti(open_cv_image)
        if isinstance(data, (list, tuple)):
            for d in data:
                if d:
                    decoded.append(d)
        else:
            if data:
                decoded.append(data)
    except Exception:
        pass
    return decoded

@app.route('/read', methods=['POST'])
def read_qr():
    if 'image' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
    file = request.files['image']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))

    try:
        pil_img = Image.open(file.stream).convert('RGB')
    except Exception as e:
        flash('Unable to open image: ' + str(e))
        return redirect(url_for('index'))

    decoded = []
    if PYZBAR_AVAILABLE:
        decoded = decode_with_pyzbar(pil_img)
    if not decoded:
        decoded = decode_with_opencv(pil_img)

    decoded = list(dict.fromkeys(decoded))

    return render_template('index.html', decoded_list=decoded)

@app.route('/demo_qr')
def demo_qr():
    content = 'https://example.com'
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#000000', back_color='#ffffff').convert('RGB')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)
