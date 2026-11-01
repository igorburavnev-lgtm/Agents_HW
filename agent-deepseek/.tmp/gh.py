import json, urllib.request, urllib.error
for url in ["https://api.github.com/repos/RussianInvestments/invest-python",
            "https://api.github.com/repos/Tinkoff/invest-python"]:
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"x"}), timeout=30))
        print(f"OK   {url} -> {d['full_name']} stars={d['stargazers_count']} archived={d['archived']} pushed={d['pushed_at']}")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} {url}")
    except Exception as e:
        print(f"ERR {url}: {e}")
