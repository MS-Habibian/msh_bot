# import requests

# def search_openalex(query: str, page: int = 1, per_page: int = 5) -> list:
#     # URL encode the query if needed, and add page/per_page parameters
#     url = f"https://api.openalex.org/works?search={query}&page={page}&per_page={per_page}"
    
#     try:
#         response = requests.get(url, timeout=10)
#         response.raise_for_status()
#         data = response.json()
        
#         results = []
#         for work in data.get('results', []):
#             title = work.get('title', 'بدون عنوان')
#             year = work.get('publication_year', 'نامشخص')
#             citation = work.get('cited_by_count', 0), 
#             journal = work.get('primary_location', {}).get('source', {}).get('display_name') if work.get('primary_location') and work.get('primary_location').get('source') else 'نامشخص'
            
#             # Extract authors
#             authorships = work.get('authorships', [])
#             authors = [a['author']['display_name'] for a in authorships[:3]]
#             if len(authorships) > 3:
#                 authors.append("et al.")
#             author_str = ", ".join(authors) if authors else "نامشخص"
            
#             # Check for OA PDF
#             pdf_link = None
#             oa_data = work.get('open_access', {})
#             if oa_data.get('is_oa') and oa_data.get('oa_url'):
#                 pdf_link = oa_data.get('oa_url')
                
#             results.append({
#                 'title': title,
#                 'authors': author_str,
#                 'year': year,
#                 'pdf_link': pdf_link,
#                 'journal': journal,
#                 'citation': citation,
#             })
#         return results
#     except Exception as e:
#         print(f"OpenAlex search error: {e}")
#         return []

import requests
import urllib.parse
import xml.etree.ElementTree as ET


def search_openalex(query: str, page: int = 1, per_page: int = 5) -> list:
    try:
        url = f"https://api.openalex.org/works?search={query}&page={page}&per_page={per_page}"
        response = requests.get(url, timeout=10)
        data = response.json()
        results = []
        for work in data.get('results', []):
            authors = [author['author']['display_name'] for author in work.get('authorships', [])[:3]]
            if len(work.get('authorships', [])) > 3:
                authors.append("et al.")
            
            pdf_link = None
            oa_data = work.get('open_access', {})
            if oa_data.get('is_oa') and oa_data.get('oa_url'):
                pdf_link = oa_data.get('oa_url')
                
            # استخراج DOI تمیز شده (بدون آدرس سایت)
            doi = work.get('doi')
            if doi:
                doi = doi.replace('https://doi.org/', '')

            results.append({
                'source': 'OpenAlex',
                'title': work.get('title', 'بدون عنوان'),
                'authors': authors,
                'year': work.get('publication_year', 'نامشخص'),
                'journal': work.get('primary_location', {}).get('source', {}).get('display_name', 'نامشخص'),
                'citation': work.get('cited_by_count', 0), # مشکل کامای اضافی در فایل شما برطرف شد
                'pdf_link': pdf_link,
                'doi': doi
            })
        return results
    except Exception as e:
        print(f"OpenAlex error: {e}")
        return []

# --- 2. اضافه کردن جستجوی Crossref ---
def search_crossref(query: str, page: int = 1, per_page: int = 5) -> list:
    try:
        offset = (page - 1) * per_page
        url = f"https://api.crossref.org/works?query={urllib.parse.quote(query)}&rows={per_page}&offset={offset}"
        response = requests.get(url, timeout=10)
        data = response.json()
        results = []
        for work in data.get('message', {}).get('items', []):
            authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in work.get('author', [])[:3]]
            
            # پیدا کردن لینک PDF در کراس‌رف
            pdf_link = None
            for link in work.get('link', []):
                if link.get('content-type') == 'application/pdf':
                    pdf_link = link.get('URL')
                    break
                    
            results.append({
                'source': 'Crossref',
                'title': work.get('title', ['بدون عنوان'])[0],
                'authors': authors,
                'year': work.get('published-print', {}).get('date-parts', [[None]])[0][0] or 'نامشخص',
                'journal': work.get('container-title', ['نامشخص'])[0],
                'citation': work.get('is-referenced-by-count', 0),
                'pdf_link': pdf_link,
                'doi': work.get('DOI')
            })
        return results
    except Exception as e:
        print(f"Crossref error: {e}")
        return []

# --- 3. اضافه کردن جستجوی arXiv ---
def search_arxiv(query: str, page: int = 1, per_page: int = 5) -> list:
    try:
        start = (page - 1) * per_page
        url = f"http://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(query)}&start={start}&max_results={per_page}"
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.text)
        ns = {'arxiv': 'http://www.w3.org/2005/Atom'}
        
        results = []
        for entry in root.findall('arxiv:entry', ns):
            pdf_link = None
            for link in entry.findall('arxiv:link', ns):
                if link.get('title') == 'pdf':
                    pdf_link = link.get('href')
                    break
                    
            results.append({
                'source': 'arXiv',
                'title': entry.find('arxiv:title', ns).text.replace('\n', ' ').strip(),
                'authors': [author.find('arxiv:name', ns).text for author in entry.findall('arxiv:author', ns)[:3]],
                'year': entry.find('arxiv:published', ns).text[:4],
                'journal': 'arXiv',
                'citation': 0,
                'pdf_link': pdf_link,
                'doi': None # arXiv معمولا DOI ندارد، مگر اینکه چاپ شده باشد
            })
        return results
    except Exception as e:
        print(f"arXiv error: {e}")
        return []

# تابع کلی برای تجمیع نتایج
def search_all_sources(query: str, page: int = 1, per_page: int = 5):
    # می‌توانید بسته به نیاز، نتایج این ۳ منبع را با هم ترکیب کنید
    # در اینجا برای جلوگیری از تاخیر زیاد، فقط یکی را فراخوانی می‌کنیم یا ترکیبی می‌سازیم
    # مثال ترکیبی (هر منبع 2 نتیجه بیاورد):
    res = search_openalex(query, page, 2) + search_crossref(query, page, 2) + search_arxiv(query, page, 1)
    return res