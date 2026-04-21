import requests
from utils.google_scraper import search_google
from utils.pdf_extractor import extract_pdf_urls

user_search_cache = {}

def search_semantic_scholar(query, chat_id):
    """
    Search Semantic Scholar API for papers.
    Returns list of results with pdf_url if available.
    """
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': query,
            'limit': 10,
            'fields': 'title,authors,year,openAccessPdf'
        }
        
        response = requests.get(url, params=params, timeout=15)
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
        print(f"Semantic Scholar error: {e}")
        return []


def search_papers_via_google(query, chat_id):
    """
    Search papers using Google Search with 'filetype:pdf' query.
    Extracts PDF URLs from results.
    Returns list of results with pdf_url.
    """
    try:
        # Add filetype:pdf to query
        google_query = f'"{query}" filetype:pdf'
        search_results = search_google(google_query, num_results=10)
        
        if not search_results:
            return []
        
        # Extract PDF URLs
        pdf_urls = extract_pdf_urls(search_results)
        
        # Build results
        results = []
        for idx, result in enumerate(search_results[:len(pdf_urls) if pdf_urls else 5]):
            pdf_url = pdf_urls[idx] if idx < len(pdf_urls) else None
            
            results.append({
                'id': idx,
                'title': result.get('title', 'Unknown'),
                'author': 'Unknown',  # Google doesn't provide author
                'year': 'N/A',
                'pdf_url': pdf_url,
                'source': 'Google Search'
            })
        
        user_search_cache[chat_id] = results
        return results
    except Exception as e:
        print(f"Google search error: {e}")
        return []


def search_papers_combined(query, chat_id):
    """
    Combined search: try Semantic Scholar first, fallback to Google Search.
    """
    # Try Semantic Scholar first
    results = search_semantic_scholar(query, chat_id)
    
    # If no PDFs found, try Google
    has_pdf = any(r.get('pdf_url') for r in results)
    if not has_pdf or not results:
        google_results = search_papers_via_google(query, chat_id)
        if google_results:
            results = google_results
    
    return results
