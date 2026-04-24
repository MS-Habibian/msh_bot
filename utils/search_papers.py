
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
            
            # Clean DOI for Libgen
            raw_doi = work.get('doi', '')
            doi = raw_doi.replace('https://doi.org/', '') if raw_doi else None
            
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
                'doi': doi,
            })
        return results
    except Exception as e:
        print(f"OpenAlex search error: {e}")
        return []