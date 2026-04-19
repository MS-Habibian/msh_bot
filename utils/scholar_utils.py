import logging
import requests
from bs4 import BeautifulSoup
from scholarly import scholarly

SCIHUB_BASE_URL = "https://sci-hub.pub/"
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
    # سعی در چند دامنه مختلف
    base_urls = ['https://sci-hub.ru', 'https://sci-hub.su', 'https://sci-hub.pub']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    
    logging.info(f"Attempting to download from Sci-Hub. Identifier: {identifier}")

    for base_url in base_urls:
        try:
            url = f"{base_url}/{identifier}"
            response = requests.get(url, headers=headers, verify=False, timeout=15)
            
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            pdf_url = None

            # روش 1: پیدا کردن از طریق تگ iframe
            iframe = soup.find('iframe', id='pdf')
            if iframe and iframe.get('src'):
                pdf_url = iframe['src']
            
            # روش 2: پیدا کردن از طریق تگ embed
            if not pdf_url:
                embed = soup.find('embed', type='application/pdf')
                if embed and embed.get('src'):
                    pdf_url = embed['src']
                    
            # روش 3: پیدا کردن از طریق دکمه دانلود
            if not pdf_url:
                button = soup.find('button', onclick=re.compile(r"location\.href='(.*?)'"))
                if button:
                    match = re.search(r"location\.href='(.*?)'", button['onclick'])
                    if match:
                        pdf_url = match.group(1)

            if pdf_url:
                # اصلاح لینک‌های نسبی (مثل //domain.com/file.pdf)
                if pdf_url.startswith('//'):
                    pdf_url = 'https:' + pdf_url
                elif pdf_url.startswith('/'):
                    pdf_url = base_url + pdf_url

                logging.info(f"Found PDF URL: {pdf_url}. Downloading...")
                
                # دانلود خود فایل PDF
                pdf_response = requests.get(pdf_url, headers=headers, verify=False, timeout=20)
                
                # بررسی اینکه آیا فایل واقعاً PDF است (با چک کردن بایت‌های ابتدایی)
                if pdf_response.status_code == 200 and pdf_response.content.startswith(b'%PDF'):
                    return pdf_response.content
                else:
                    logging.error("Downloaded file is not a valid PDF.")

        except Exception as e:
            logging.warning(f"Failed to fetch from {base_url}: {e}")
            
    return None
