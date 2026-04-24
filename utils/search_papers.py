# import requests
# import urllib.parse

# def search_openalex(query, max_results=5):
#     """
#     Searches OpenAlex for papers and returns metadata + Open Access PDF links.
#     """
#     encoded_query = urllib.parse.quote(query)
#     # OpenAlex API endpoint for searching works
#     url = f"https://api.openalex.org/works?search={encoded_query}&per-page={max_results}"
    
#     results = []
#     try:
#         response = requests.get(url, timeout=15)
#         response.raise_for_status()
#         data = response.json()
        
#         for work in data.get("results", []):
#             title = work.get("title", "No Title")
            
#             # Extract authors
#             authorships = work.get("authorships", [])
#             authors = [a.get("author", {}).get("display_name", "") for a in authorships]
#             author_str = ", ".join(authors[:3])
#             if len(authors) > 3:
#                 author_str += " et al."
                
#             year = work.get("publication_year", "Unknown")
            
#             # Check for Open Access PDF link
#             pdf_link = None
#             open_access = work.get("open_access", {})
#             if open_access.get("is_oa") and open_access.get("oa_url"):
#                 pdf_link = open_access.get("oa_url")
                
#             results.append({
#                 "title": title,
#                 "authors": author_str,
#                 "year": year,
#                 "pdf_link": pdf_link
#             })
            
#     except Exception as e:
#         print(f"Error fetching from OpenAlex: {e}")
        
#     return results


# In search_papers.py
import requests

def search_openalex(query: str, page: int = 1, per_page: int = 5, from_year: str = None) -> list:
    url = f"https://api.openalex.org/works?search={query}&page={page}&per_page={per_page}"
    
    if from_year:
        url += f"&filter=from_publication_date:{from_year}-01-01"
        
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for work in data.get('results', []):
            title = work.get('title', 'بدون عنوان')
            year = work.get('publication_year', 'نامشخص')
            citation = work.get('cited_by_count', 0)
            journal = work.get('primary_location', {}).get('source', {}).get('display_name') if work.get('primary_location') and work.get('primary_location').get('source') else 'نامشخص'
            
            authorships = work.get('authorships', [])
            authors = [a['author']['display_name'] for a in authorships[:3]]
            if len(authorships) > 3:
                authors.append("et al.")
            author_str = ", ".join(authors) if authors else "نامشخص"
            
            # جستجوی دقیق برای لینک مستقیم PDF
            pdf_link = None
            best_oa = work.get('best_oa_location') or {}
            
            if best_oa.get('pdf_url'):
                pdf_link = best_oa.get('pdf_url')
            else:
                # جستجو در سایر لوکیشن‌ها برای پیدا کردن pdf_url
                for loc in work.get('locations', []):
                    if loc.get('pdf_url'):
                        pdf_link = loc.get('pdf_url')
                        break
                
                # اگر هیچ pdf_url ای نبود ولی لینک open access داشت
                if not pdf_link and work.get('open_access', {}).get('oa_url'):
                    pdf_link = work['open_access']['oa_url']
                
            results.append({
                'title': title,
                'authors': author_str,
                'year': year,
                'pdf_link': pdf_link,
                'journal': journal,
                'citation': citation,
            })
        return results
    except Exception as e:
        print(f"OpenAlex search error: {e}")
        return []