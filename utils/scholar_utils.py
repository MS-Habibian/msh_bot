import requests
from bs4 import BeautifulSoup
from scholarly import scholarly

SCIHUB_BASE_URL = "https://sci-hub.su/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# حافظه موقت نتایج جستجو
user_search_cache = {}

def get_scholar_results(query, limit=10):
    search_query = scholarly.search_pubs(query)
    results = []
    for _ in range(limit):
        try:
            results.append(next(search_query))
        except StopIteration:
            break
    return results

def get_scihub_pdf(identifier):
    # درخواست به سای‌هاب
    response = requests.post(SCIHUB_BASE_URL, data={'request': identifier}, headers=HEADERS, timeout=30, verify=False)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    pdf_iframe = soup.find('iframe', id='pdf') or soup.find('embed', id='pdf')
    
    if not pdf_iframe or not pdf_iframe.get('src'):
        return None # فایل یافت نشد
        
    pdf_url = pdf_iframe.get('src')
    if pdf_url.startswith('//'):
        pdf_url = 'https:' + pdf_url
    elif pdf_url.startswith('/'):
        pdf_url = SCIHUB_BASE_URL.rstrip('/') + pdf_url
        
    # دانلود فایل
    pdf_response = requests.get(pdf_url, headers=HEADERS, timeout=60, verify=False)
    
    if pdf_response.status_code == 200:
        return pdf_response.content
    return None
