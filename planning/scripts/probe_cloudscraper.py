import cloudscraper

scraper = cloudscraper.create_scraper()
urls = [
    "https://community.bistudio.com/wiki/api.php?action=query&format=json&meta=siteinfo",
    "https://community.bistudio.com/api.php?action=query&format=json&meta=siteinfo",
    "https://community.bistudio.com/wiki/DayZ:Enforce_Script_Syntax"
]

for url in urls:
    try:
        resp = scraper.get(url, timeout=10)
        print(f"URL: {url}")
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text[:200]}\n")
    except Exception as e:
        print(f"URL: {url}")
        print(f"Error: {e}\n")
