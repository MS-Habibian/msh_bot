# utils/google_scraper.py
from duckduckgo_search import DDGS


def search_google(query, num_results=10):
    """
    Searches the web using DuckDuckGo to bypass Google's bot protections.
    Keeps the function name 'search_google' so you don't have to change your imports.
    """
    results = []
    print("\n\n input query: ", query)
    try:
        with DDGS() as ddgs:
            # max_results limits the number of fetched items
            search_results = ddgs.text(query, max_results=num_results)
            print("search res:", search_results)
            for res in search_results:
                print("res:", res)
                results.append(
                    {
                        "title": res.get("title", "بدون عنوان"),  # Default fallback
                        "link": res.get("href", ""),
                        "snippet": res.get(
                            "body", "توضیحاتی در دسترس نیست."
                        ),  # Default fallback
                    }
                )

        return results

    except Exception as e:
        print(f"Search error: {e}")
        return None
