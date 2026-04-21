import requests
import time

user_search_cache = {}

def search_semantic_scholar(query, chat_id, retry_count=0):
    """
    Search Semantic Scholar API for papers with rate limit handling.
    """
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': query,
            'limit': 10,
            'fields': 'title,authors,year,openAccessPdf'
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        # Handle rate limiting
        if response.status_code == 429:
            if retry_count < 2:
                wait_time = 3 * (retry_count + 1)
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
                return search_semantic_scholar(query, chat_id, retry_count + 1)
            else:
                print("Rate limit exceeded, falling back to Google")
                return []
        
        response.raise_for_status()
        data = response.json()
        
        results = []
        for idx, paper in enumerate(data.get('data', [])):
            title = paper.get('title', 'Unknown')
            authors = paper.get('authors', [])
            author = authors[0].get('name', 'Unknown') if authors else 'Unknown'
            year = paper.get('year', 'N/A')
            
            pdf_url = None
            open_access = paper.get('openAccessPdf')
            if open_access:
                pdf_url = open_access.get('url')
            
            results.append({
                'id': idx,
                'title': title,
                'author': author,
                'year': year,
                'pdf_url': pdf_url
            })
        
        user_search_cache[chat_id] = results
        return results
        
    except Exception as e:
        print(f"Error in Semantic Scholar API: {e}")
        return []


def search_papers_via_google(query, chat_id):
    """
    Fallback: Search papers using Google with filetype:pdf.
    """
    try:
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        google_query = f'"{query}" filetype:pdf'
        search_url = f"https://www.google.com/search?q={requests.utils.quote(google_query)}&num=10"
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for idx, g in enumerate(soup.find_all('div', class_='g')[:10]):
            title_elem = g.find('h3')
            link_elem = g.find('a')
            
            if title_elem and link_elem:
                title = title_elem.get_text()
                link = link_elem.get('href')
                
                if link and link.startswith('http'):
                    # Check if it's a direct PDF
                    pdf_url = None
                    if link.lower().endswith('.pdf'):
                        pdf_url = link
                    elif 'arxiv.org' in link and '/abs/' in link:
                        pdf_url = link.replace('/abs/', '/pdf/') + '.pdf'
                    elif 'arxiv.org' in link and '/pdf/' in link:
                        pdf_url = link
                    
                    results.append({
                        'id': idx,
                        'title': title,
                        'author': 'Unknown',
                        'year': 'N/A',
                        'pdf_url': pdf_url
                    })
        
        user_search_cache[chat_id] = results
        return results
        
    except Exception as e:
        print(f"Error in Google search: {e}")
        return []


def search_papers_combined(query, chat_id):
    """
    Try Semantic Scholar first, fallback to Google if rate limited or no PDFs.
    """
    results = search_semantic_scholar(query, chat_id)
    
    # Fallback to Google if no results or no PDFs
    has_pdf = any(r.get('pdf_url') for r in results)
    if not has_pdf or not results:
        google_results = search_papers_via_google(query, chat_id)
        if google_results:
            results = google_results
    
    return results
