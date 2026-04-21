import re
import requests
from bs4 import BeautifulSoup

def extract_pdf_urls(search_results, max_check=5):
    """
    Given Google search results, extract direct PDF URLs.
    Returns list of PDF URLs found.
    """
    pdf_urls = []
    
    for result in search_results[:max_check]:
        link = result.get('link', '')
        
        # Direct PDF link
        if link.lower().endswith('.pdf'):
            pdf_urls.append(link)
            continue
        
        # arXiv PDF
        if 'arxiv.org' in link:
            if '/abs/' in link:
                pdf_link = link.replace('/abs/', '/pdf/') + '.pdf'
                pdf_urls.append(pdf_link)
            elif '/pdf/' in link:
                pdf_urls.append(link)
            continue
        
        # Semantic Scholar
        if 'semanticscholar.org' in link:
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                resp = requests.get(link, headers=headers, timeout=10, allow_redirects=True)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Look for PDF button/link
                pdf_link = soup.find('a', href=re.compile(r'\.pdf$'))
                if pdf_link:
                    pdf_url = pdf_link.get('href')
                    if not pdf_url.startswith('http'):
                        pdf_url = 'https://semanticscholar.org' + pdf_url
                    pdf_urls.append(pdf_url)
            except:
                pass
            continue
        
        # Check if page contains direct PDF link
        if link.startswith('http'):
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                resp = requests.head(link, headers=headers, timeout=5, allow_redirects=True)
                content_type = resp.headers.get('Content-Type', '')
                
                if 'application/pdf' in content_type:
                    pdf_urls.append(link)
            except:
                pass
    
    return pdf_urls
