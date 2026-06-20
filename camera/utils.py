from PIL import Image
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

def process_kitchen_image(image_path):
    """
    Processes the kitchen image with optimized steps.
    """
    try:
        with Image.open(image_path) as img:
            # Resize image (maintain aspect ratio)
            img.thumbnail((800, 600))  # Thumbnail maintains aspect ratio

            # Convert to RGB (if needed) for uniformity
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Save as optimized format (e.g., JPEG with quality)
            img.save(image_path, "JPEG", quality=85, optimize=True)



    except Exception as e:
        pass

def handle_uploaded_file(file):
    """
    Saves an uploaded file to a temporary location.
    """
    file_name = default_storage.save(file.name, ContentFile(file.read()))
    file_path = default_storage.path(file_name)
    return file_path