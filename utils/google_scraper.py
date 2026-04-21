# # utils/google_scraper.py
# from ddgs import DDGS


# def search_google(query, num_results=10):
#     """
#     Searches the web using DuckDuckGo to bypass Google's bot protections.
#     Keeps the function name 'search_google' so you don't have to change your imports.
#     """
#     results = []
#     print(f"\n\n input query: {query}")

#     try:
#         with DDGS() as ddgs:
#             # max_results limits the number of fetched items
#             search_results = list(ddgs.text(query, max_results=num_results))
#             print("search res:", search_results)

#             for res in search_results:
#                 print("res:", res)
#                 results.append(
#                     {
#                         "title": res.get(
#                             "title", "بدون عنوان"
#                         ),  # Default fallback in Persian
#                         "link": res.get("href", ""),
#                         "snippet": res.get(
#                             "body", "توضیحاتی در دسترس نیست."
#                         ),  # Default fallback in Persian
#                     }
#                 )

#         return results

#     except Exception as e:
#         print(f"Search error: {e}")
#         return None

import requests
from bs4 import BeautifulSoup
import time

def search_google(query, num_results=10):
    """
    Search Google and return results with title, link, snippet.
    Returns list of dicts: [{'title': ..., 'link': ..., 'snippet': ...}, ...]
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num={num_results}"
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for g in soup.find_all('div', class_='g'):
            title_elem = g.find('h3')
            link_elem = g.find('a')
            snippet_elem = g.find('div', class_=['VwiC3b', 'yXK7lf'])
            
            if title_elem and link_elem:
                title = title_elem.get_text()
                link = link_elem.get('href')
                snippet = snippet_elem.get_text() if snippet_elem else ""
                
                if link and link.startswith('http'):
                    results.append({
                        'title': title,
                        'link': link,
                        'snippet': snippet
                    })
        
        return results
    except Exception as e:
        print(f"Google search error: {e}")
        return []

