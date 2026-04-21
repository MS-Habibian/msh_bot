import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

def search_arxiv(query: str, max_results: int = 5) -> list:
    """Searches ArXiv and returns up to `max_results` papers with metadata."""
    safe_query = urllib.parse.quote(query)
    url = f'http://export.arxiv.org/api/query?search_query=all:{safe_query}&start=0&max_results={max_results}'
    
    response = urllib.request.urlopen(url).read()
    root = ET.fromstring(response)
    ns = {'arxiv': 'http://www.w3.org/2005/Atom'}
    
    papers = []
    for entry in root.findall('arxiv:entry', ns):
        title = entry.find('arxiv:title', ns).text.strip().replace('\n', ' ')
        
        # Extract authors (limit to first 3 + et al.)
        authors = [author.find('arxiv:name', ns).text for author in entry.findall('arxiv:author', ns)]
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        
        # Extract published year
        published = entry.find('arxiv:published', ns).text[:4]
        
        pdf_link = None
        for link in entry.findall('arxiv:link', ns):
            if link.attrib.get('title') == 'pdf':
                pdf_link = link.attrib.get('href') + ".pdf"
                break
                
        if pdf_link:
            papers.append({
                'title': title,
                'authors': author_str,
                'year': published,
                'pdf_link': pdf_link
            })
            
    return papers
