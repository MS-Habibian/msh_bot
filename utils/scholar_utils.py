import requests
from scholarly import scholarly
import cloudscraper
import urllib3

# دیکشنری برای ذخیره نتایج کاربر
# فرمت: { chat_id: [{'title': '...', 'eprint_url': '...'}, ...] }
user_search_cache = {}

def get_scholar_results(query, limit=10):
    search_query = scholarly.search_pubs(query)
    results = []
    
    for i in range(limit):
        try:
            paper = next(search_query)
            # استخراج اطلاعات لازم، از جمله eprint_url در صورت وجود
            result_data = {
                'title': paper.get('bib', {}).get('title', 'بدون عنوان'),
                'author': paper.get('bib', {}).get('author', 'نویسنده نامشخص'),
                'pub_year': paper.get('bib', {}).get('pub_year', 'سال نامشخص'),
                'pub_url': paper.get('pub_url', ''),
                'eprint_url': paper.get('eprint_url', None) # مهم: لینک مستقیم PDF
            }
            results.append(result_data)
        except StopIteration:
            break
            
    return results

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_direct_pdf(pdf_url):
    """دانلود مستقیم فایل با استفاده از cloudscraper"""
    if not pdf_url:
        return None
        
    try:
        scraper = cloudscraper.create_scraper()
        
        # مقدار verify=False را از اینجا حذف کردیم
        response = scraper.get(pdf_url, timeout=30)
        response.raise_for_status()
        
        # بررسی اینکه آیا فایل واقعا PDF است
        if response.content.startswith(b'%PDF'):
            return response.content
        else:
            print(f"File is not a PDF. URL: {pdf_url}")
            
    except Exception as e:
        print(f"Error downloading direct PDF: {e}")
        
    return None
