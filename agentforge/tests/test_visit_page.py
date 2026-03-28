import sys
import os

# Add package root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from xiaochen_agent_v2.utils.web_search import visit_page

def test_visit_page():
    # Test a known URL (e.g., example.com or a search result from previous tests)
    # Using example.com as it's stable
    url = "https://example.com"
    print(f"Testing visit_page with {url}...")
    
    success, error, content = visit_page(url)
    
    if success:
        print("SUCCESS!")
        print("-" * 20)
        print(content[:500]) # Print first 500 chars
        print("-" * 20)
    else:
        print(f"FAILURE: {error}")

    # Test a search result URL (e.g. python docs if possible, or just another stable site)
    url2 = "https://www.python.org"
    print(f"\nTesting visit_page with {url2}...")
    success2, error2, content2 = visit_page(url2)
    if success2:
        print("SUCCESS!")
        print("-" * 20)
        print(content2[:500])
        print("-" * 20)
    else:
        print(f"FAILURE: {error2}")

if __name__ == "__main__":
    test_visit_page()
