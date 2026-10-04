import os

BASE_DIR = r"C:\Users\TRSI\VSCode\Projects\Exam Schedule CSP"
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "static", "downloads")
ALLOWED_EXTENSIONS = {"xlsx", "xls"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

# إنشاء المجلدات المطلوبة إذا لم تكن موجودة
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
