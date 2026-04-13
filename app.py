from flask import Flask, render_template, request, send_file, jsonify
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import RadialGradiantColorMask
from PIL import Image
import io
import os
import uuid
import base64

app = Flask(__name__)

# Create a directory for temporary QR codes
TEMP_DIR = "temp_qr"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def generate_basic_qr(data, fill_color="black", back_color="white"):
    """Generate a basic QR code with custom colors"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    return img

def generate_styled_qr(data, style_type="rounded"):
    """Generate a styled QR code"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    
    qr.add_data(data)
    qr.make(fit=True)
    
    if style_type == "rounded":
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
        )
    elif style_type == "gradient":
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
            color_mask=RadialGradiantColorMask(
                center_color=(0, 0, 255),
                edge_color=(255, 0, 0)
            )
        )
    else:  # default
        img = qr.make_image()
    
    return img

def generate_qr_with_logo(data, logo_path=None):
    """Generate QR code with a logo in the center"""
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create QR code image
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    if logo_path and os.path.exists(logo_path):
        # Calculate logo size (25% of QR code size for better scanning)
        qr_width, qr_height = qr_img.size
        logo_size = int(qr_width * 0.25)
        
        # Open and resize logo
        logo = Image.open(logo_path)
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        
        # Calculate position to paste logo
        pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
        
        # Create a white background for the logo area
        white_bg = Image.new('RGB', (logo_size, logo_size), 'white')
        qr_img.paste(white_bg, pos)
        
        # Paste logo onto QR code
        if logo.mode == 'RGBA':
            qr_img.paste(logo, pos, logo)
        else:
            qr_img.paste(logo, pos)
    
    return qr_img

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.form.get('data', '')
        qr_type = request.form.get('qr_type', 'basic')
        fill_color = request.form.get('fill_color', 'black')
        back_color = request.form.get('back_color', 'white')
        style = request.form.get('style', 'rounded')
        
        if not data:
            return jsonify({'error': 'Please enter a URL or text'}), 400
        
        # Generate QR code based on type
        if qr_type == 'basic':
            img = generate_basic_qr(data, fill_color, back_color)
        elif qr_type == 'styled':
            img = generate_styled_qr(data, style)
        elif qr_type == 'logo':
            # Check if logo file was uploaded
            logo_file = request.files.get('logo')
            logo_path = None
            
            if logo_file and logo_file.filename:
                # Save uploaded logo temporarily
                logo_filename = f"{uuid.uuid4().hex}_{logo_file.filename}"
                logo_path = os.path.join(TEMP_DIR, logo_filename)
                logo_file.save(logo_path)
            
            img = generate_qr_with_logo(data, logo_path)
            
            # Clean up logo file
            if logo_path and os.path.exists(logo_path):
                os.remove(logo_path)
        else:
            img = generate_basic_qr(data, fill_color, back_color)
        
        # Save image to bytes buffer
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Convert to base64 for display
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'image': img_base64,
            'data': data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.json.get('data', '')
        qr_type = request.json.get('qr_type', 'basic')
        fill_color = request.json.get('fill_color', 'black')
        back_color = request.json.get('back_color', 'white')
        style = request.json.get('style', 'rounded')
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Generate QR code based on type
        if qr_type == 'basic':
            img = generate_basic_qr(data, fill_color, back_color)
        elif qr_type == 'styled':
            img = generate_styled_qr(data, style)
        elif qr_type == 'logo':
            img = generate_qr_with_logo(data, None)
        else:
            img = generate_basic_qr(data, fill_color, back_color)
        
        # Save image to bytes buffer
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return send_file(
            img_buffer,
            mimetype='image/png',
            as_attachment=True,
            download_name='qrcode.png'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)