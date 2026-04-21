import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

def search_arxiv(query: str, max_results: int = 1) -> list:
    """Searches ArXiv and returns a list of papers with direct PDF links."""
    safe_query = urllib.parse.quote(query)
    url = f'http://export.arxiv.org/api/query?search_query=all:{safe_query}&start=0&max_results={max_results}'
    
    response = urllib.request.urlopen(url).read()
    root = ET.fromstring(response)
    ns = {'arxiv': 'http://www.w3.org/2005/Atom'}
    
    papers = []
    for entry in root.findall('arxiv:entry', ns):
        title = entry.find('arxiv:title', ns).text.strip().replace('\n', ' ')
        
        pdf_link = None
        for link in entry.findall('arxiv:link', ns):
            if link.attrib.get('title') == 'pdf':
                pdf_link = link.attrib.get('href') + ".pdf"
                break
                
        if pdf_link:
            papers.append({
                'title': title,
                'pdf_link': pdf_link
            })
            
    return papers
