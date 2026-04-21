# # import urllib.request
# # import urllib.parse
# import urllib.request
# import urllib.parse
# import json
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



# def get_paper_pdf_url(paper_id: str):
#     """Fetches the direct PDF URL for a specific paperId if it exists."""
#     url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}?fields=openAccessPdf"
#     try:
#         req = urllib.request.Request(url, headers={'User-Agent': 'TelegramBot/1.0'})
#         with urllib.request.urlopen(req, timeout=10) as response:
#             data = json.loads(response.read().decode())
#             if data.get('openAccessPdf'):
#                 return data['openAccessPdf']['url']
#             return None
#     except Exception as e:
#         print(f"Error fetching PDF URL: {e}")
#         return None

import requests
import urllib.parse

def search_openalex(query, max_results=5):
    """
    Searches OpenAlex for papers and returns metadata + Open Access PDF links.
    """
    encoded_query = urllib.parse.quote(query)
    # OpenAlex API endpoint for searching works
    url = f"https://api.openalex.org/works?search={encoded_query}&per-page={max_results}"
    
    results = []
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        for work in data.get("results", []):
            title = work.get("title", "No Title")
            
            # Extract authors
            authorships = work.get("authorships", [])
            authors = [a.get("author", {}).get("display_name", "") for a in authorships]
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += " et al."
                
            year = work.get("publication_year", "Unknown")
            
            # Check for Open Access PDF link
            pdf_link = None
            open_access = work.get("open_access", {})
            if open_access.get("is_oa") and open_access.get("oa_url"):
                pdf_link = open_access.get("oa_url")
                
            results.append({
                "title": title,
                "authors": author_str,
                "year": year,
                "pdf_link": pdf_link
            })
            
    except Exception as e:
        print(f"Error fetching from OpenAlex: {e}")
        
    return results
