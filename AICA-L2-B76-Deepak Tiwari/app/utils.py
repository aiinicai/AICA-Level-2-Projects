import os
import cv2
import numpy as np
from PIL import Image, ImageTk

def pil_to_cv2(pil_image):
    """Converts PIL Image to OpenCV BGR numpy array."""
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    rgb = np.array(pil_image)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return bgr

def cv2_to_pil(cv2_image):
    """Converts OpenCV BGR numpy array to PIL RGB Image."""
    if len(cv2_image.shape) == 2:  # Grayscale
        rgb = cv2.cvtColor(cv2_image, cv2.COLOR_GRAY2RGB)
    else:
        rgb = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)

def rotate_pil_image(pil_img, angle):
    """
    Rotates a PIL Image by arbitrary angle in degrees counter-clockwise or clockwise.
    Angle in degrees: positive = counter-clockwise in PIL default (or clockwise depending on expand).
    For standard document rotation (90, 180, 270 degrees clockwise):
    PIL image.rotate(-angle, expand=True) rotates clockwise.
    """
    if angle % 360 == 0:
        return pil_img.copy()
    
    # Standard 90, 180, 270 CW rotation
    if angle in [90, 180, 270]:
        # PIL rotate angle is counter-clockwise, so -angle rotates clockwise
        return pil_img.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC)
    else:
        return pil_img.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC, fillcolor=(255, 255, 255))

def create_thumbnail(pil_img, max_size=(160, 220)):
    """Creates a high-quality downsampled PIL thumbnail respecting aspect ratio."""
    thumb = pil_img.copy()
    thumb.thumbnail(max_size, Image.Resampling.LANCZOS)
    return thumb

def pil_to_photoimage(pil_img):
    """Converts PIL image to Tkinter ImageTk.PhotoImage."""
    return ImageTk.PhotoImage(pil_img)

def format_file_size(size_in_bytes):
    """Formats raw file size into human readable string (KB, MB)."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    else:
        return f"{size_in_bytes / (1024 * 1024):.2f} MB"
