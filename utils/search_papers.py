# import urllib.request
# import urllib.parse
# import xml.etree.ElementTree as ET

# def search_arxiv(query: str, max_results: int = 5) -> list:
#     """Searches ArXiv and returns up to `max_results` papers with metadata."""
#     safe_query = urllib.parse.quote(query)
#     url = f'http://export.arxiv.org/api/query?search_query=all:{safe_query}&start=0&max_results={max_results}'
    
#     try:
#       response = urllib.request.urlopen(url, timeout=10).read()
#     except Exception as e:
#       print(f"ArXiv search error: {e}")
#       return [] # Return empty list if it times out or fails
#     root = ET.fromstring(response)
#     ns = {'arxiv': 'http://www.w3.org/2005/Atom'}
    
#     papers = []
#     for entry in root.findall('arxiv:entry', ns):
#         title = entry.find('arxiv:title', ns).text.strip().replace('\n', ' ')
        
#         # Extract authors (limit to first 3 + et al.)
#         authors = [author.find('arxiv:name', ns).text for author in entry.findall('arxiv:author', ns)]
#         author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        
#         # Extract published year
#         published = entry.find('arxiv:published', ns).text[:4]
        
#         pdf_link = None
#         for link in entry.findall('arxiv:link', ns):
#             if link.attrib.get('title') == 'pdf':
#                 pdf_link = link.attrib.get('href') + ".pdf"
#                 break
                
#         if pdf_link:
#             papers.append({
#                 'title': title,
#                 'authors': author_str,
#                 'year': published,
#                 'pdf_link': pdf_link
#             })
            
#     return papers

import urllib.request
import urllib.parse
import json

def search_semantic_scholar(query: str, max_results: int = 5):
    """
    Searches Semantic Scholar and returns a list of papers.
    Requested fields: paperId, title, authors, year, openAccessPdf
    """
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": max_results,
        "fields": "paperId,title,authors,year,openAccessPdf"
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        # Adding a User-Agent is good practice to prevent getting blocked by the API
        req = urllib.request.Request(url, headers={'User-Agent': 'TelegramBot/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            papers = data.get('data', [])
            
            # Format authors for readability
            for paper in papers:
                authors_list = paper.get('authors', [])
                if authors_list:
                    names = [a['name'] for a in authors_list]
                    if len(names) > 3:
                        paper['formatted_authors'] = f"{', '.join(names[:3])} et al."
                    else:
                        paper['formatted_authors'] = ", ".join(names)
                else:
                    paper['formatted_authors'] = "Unknown Authors"
                    
            return papers
            
    except Exception as e:
        print(f"Semantic Scholar API Error: {e}")
        return []

def get_paper_pdf_url(paper_id: str):
    """Fetches the direct PDF URL for a specific paperId if it exists."""
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}?fields=openAccessPdf"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'TelegramBot/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get('openAccessPdf'):
                return data['openAccessPdf']['url']
            return None
    except Exception as e:
        print(f"Error fetching PDF URL: {e}")
        return None

