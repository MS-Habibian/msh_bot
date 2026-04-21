import requests
from scholarly import scholarly

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

def download_direct_pdf(pdf_url):
    """دانلود مستقیم فایل از لینک eprint_url"""
    if not pdf_url:
        return None
        
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(pdf_url, headers=headers, timeout=20, verify=False)
        response.raise_for_status()
        
        # بررسی اینکه آیا فایل واقعا PDF است
        if response.content.startswith(b'%PDF'):
            return response.content
            
    except Exception as e:
        print(f"Error downloading direct PDF: {e}")
        
    return None
