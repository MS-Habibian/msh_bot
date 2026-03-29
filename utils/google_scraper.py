# utils/google_scraper.py
import requests
from bs4 import BeautifulSoup

def search_google(query, num_results=10):
    url = f"https://www.google.com/search?q={query}&num={num_results}"
    
    # We must use a valid User-Agent, otherwise Google will block the request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None
        
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    
    # Google's search results are typically inside div tags with class 'g'
    for g in soup.find_all('div', class_='g'):
        anchors = g.find_all('a')
        
        if anchors:
            link = anchors[0]['href']
            title = g.find('h3')
            snippet = g.find('div', {'style': '-webkit-line-clamp:2'}) # Common snippet container
            
            # Fallback for snippet if the specific style isn't found
            if not snippet:
                snippet = g.find('div', class_='VwiC3b')
                
            if title and link.startswith('http'):
                results.append({
                    "title": title.text,
                    "link": link,
                    "snippet": snippet.text if snippet else "No description available."
                })
                
        if len(results) >= num_results:
            break
            
    return results
