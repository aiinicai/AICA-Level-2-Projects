import io
import base64
import barcode
from barcode.writer import ImageWriter
import qrcode
from PIL import Image

def generate_barcode_image(asset_id: str, writer_options: dict = None) -> Image.Image:
    """
    Generates a Code 128 barcode image encoding Asset ID only.
    """
    options = {
        'module_width': 0.3,
        'module_height': 12.0,
        'quiet_zone': 3.0,
        'font_size': 10,
        'text_distance': 4.0,
        'write_text': False  # We render human-readable text cleanly in template layout
    }
    if writer_options:
        options.update(writer_options)

    code128 = barcode.get_barcode_class('code128')
    barcode_instance = code128(asset_id, writer=ImageWriter())
    
    buffer = io.BytesIO()
    barcode_instance.write(buffer, options=options)
    buffer.seek(0)
    return Image.open(buffer).convert("RGBA")

def generate_qr_image(asset_id: str, box_size: int = 10, border: int = 2) -> Image.Image:
    """
    Generates a high-quality QR code image encoding Asset ID only.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(asset_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    return img

def image_to_base64_data_uri(img: Image.Image, format: str = "PNG") -> str:
    """
    Converts a PIL image to a Base64 Data URI string.
    """
    buffered = io.BytesIO()
    img.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/{format.lower()};base64,{img_str}"

def get_code_base64(asset_id: str, code_type: str = "BARCODE") -> str:
    """
    Helper to get base64 encoded barcode or QR for asset ID.
    """
    if code_type.upper() == "QR_CODE" or code_type.upper() == "QR":
        img = generate_qr_image(asset_id)
    else:
        img = generate_barcode_image(asset_id)
    return image_to_base64_data_uri(img)
