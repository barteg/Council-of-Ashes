from duckduckgo_search import DDGS

class SearchService:
    def __init__(self):
        self.ddgs = DDGS()

    def search_terms(self, terms):
        results = {}
        if not terms:
            return results
            
        print(f"[SEARCH] Looking up terms: {terms}")
        for term in terms:
            try:
                # Get the first 2 relevant results
                search_results = self.ddgs.text(term, max_results=2)
                summary = " ".join([r['body'] for r in search_results])
                results[term] = summary[:500] # Limit to 500 chars per term
            except Exception as e:
                print(f"[SEARCH] Error searching for '{term}': {e}")
                results[term] = "No context found."
        return results

search_service = SearchService()
