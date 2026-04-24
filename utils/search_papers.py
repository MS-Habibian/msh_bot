import requests

def search_openalex(query: str, page: int = 1, per_page: int = 5) -> list:
    # URL encode the query if needed, and add page/per_page parameters
    url = f"https://api.openalex.org/works?search={query}&page={page}&per_page={per_page}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for work in data.get('results', []):
            title = work.get('title', 'بدون عنوان')
            year = work.get('publication_year', 'نامشخص')
            citation = work.get('cited_by_count', 0), 
            journal = work.get('primary_location', {}).get('source', {}).get('display_name') if work.get('primary_location') and work.get('primary_location').get('source') else 'نامشخص'
            doi = work.get('doi')
            if doi and doi.startswith('https://doi.org/'):
                doi = doi.replace('https://doi.org/', '')
            
            # Extract authors
            authorships = work.get('authorships', [])
            authors = [a['author']['display_name'] for a in authorships[:3]]
            if len(authorships) > 3:
                authors.append("et al.")
            author_str = ", ".join(authors) if authors else "نامشخص"
            
            # Check for OA PDF
            pdf_link = None
            oa_data = work.get('open_access', {})
            if oa_data.get('is_oa') and oa_data.get('oa_url'):
                pdf_link = oa_data.get('oa_url')
                
            results.append({
                'title': title,
                'authors': author_str,
                'year': year,
                'pdf_link': pdf_link,
                'journal': journal,
                'citation': citation,
                'doi': doi,
            })
        return results
    except Exception as e:
        print(f"OpenAlex search error: {e}")
        return []
