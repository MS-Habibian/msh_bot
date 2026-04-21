# utils/scholar_utils.py
import requests

# دیکشنری برای ذخیره موقت نتایج جستجوی هر کاربر (برای دریافت لینک در مرحله دانلود)
user_search_cache = {}

def search_semantic_scholar(query, chat_id):
    """
    جستجوی مقاله با استفاده از Semantic Scholar API.
    فقط مقالاتی که لینک مستقیم PDF (Open Access) دارند را در اولویت قرار می‌دهد.
    """
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        'query': query,
        'fields': 'title,authors,year,openAccessPdf',
        'limit': 10
    }
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for index, item in enumerate(data.get('data', [])):
            pdf_url = None
            if item.get('openAccessPdf'):
                pdf_url = item['openAccessPdf'].get('url')
            
            # استخراج نام اولین نویسنده (برای نمایش خلاصه)
            authors = item.get('authors', [])
            author_name = authors[0]['name'] if authors else "Unknown"

            results.append({
                'id': index,
                'title': item.get('title', 'بدون عنوان'),
                'year': item.get('year', 'نامشخص'),
                'author': author_name,
                'pdf_url': pdf_url
            })
            
        # ذخیره نتایج در کش برای این کاربر
        user_search_cache[chat_id] = results
        return results

    except Exception as e:
        print(f"Error in Semantic Scholar API: {e}")
        return []
