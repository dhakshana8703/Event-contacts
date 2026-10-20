import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from src.providers.search_serper import SerperSearchProvider

def main():
    s = SerperSearchProvider()
    q = 'Mario Boselli "23 April 2015" "Arab Fashion Council"'
    print(f"Searching: {q}")
    results = s.search(q, num_results=5)
    for r in results:
        print("URL:", r.url)
        print("Title:", r.title)
        print("Snippet:", r.snippet)
        print("-" * 60)

if __name__ == "__main__":
    main()
