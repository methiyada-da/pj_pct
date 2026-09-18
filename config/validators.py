from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_IMAGE_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def validate_uploaded_image(uploaded_file, max_size=MAX_IMAGE_SIZE):
    """ตรวจขนาด ชนิด และเนื้อหาไฟล์รูปก่อนบันทึกลง storage"""
    if not uploaded_file:
        return

    if uploaded_file.size > max_size:
        raise ValidationError('ขนาดรูปภาพต้องไม่เกิน 5 MB')

    extension = Path(uploaded_file.name or '').suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError('รองรับเฉพาะไฟล์ JPG, PNG หรือ WebP เท่านั้น')

    content_type = (getattr(uploaded_file, 'content_type', '') or '').lower()
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValidationError('ชนิดไฟล์รูปภาพไม่ถูกต้อง')

    try:
        image = Image.open(uploaded_file)
        image.verify()
        if image.format not in ALLOWED_IMAGE_FORMATS:
            raise ValidationError('รูปแบบไฟล์รูปภาพไม่รองรับ')
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise ValidationError('ไฟล์ที่อัปโหลดไม่ใช่รูปภาพที่ถูกต้อง') from error
    finally:
        uploaded_file.seek(0)
