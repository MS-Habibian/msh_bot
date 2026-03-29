# utils/web_downloader.py
import subprocess
import os
import uuid

def download_single_html(url: str, downloads_dir: str = "downloads"):
    """
    دانلود صفحه وب به صورت یک فایل HTML واحد با استفاده از monolith
    """
    # ایجاد پوشه دانلود در صورت عدم وجود
    os.makedirs(downloads_dir, exist_ok=True)
    
    # ایجاد یک نام تصادفی برای فایل خروجی
    task_id = str(uuid.uuid4())[:8]
    output_file = os.path.join(downloads_dir, f"page_{task_id}.html")
    
    # دستور اجرایی monolith
    command = ["monolith", "-o", output_file, url]
    
    try:
        # اجرای دستور در ترمینال
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(output_file):
            return output_file
        return None
    except subprocess.CalledProcessError:
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def cleanup_file(filepath: str):
    """
    حذف فایل پس از ارسال برای خالی نگه داشتن فضای سرور
    """
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Cleanup error: {e}")
