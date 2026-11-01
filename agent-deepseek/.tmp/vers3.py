import json, urllib.request, urllib.error
for n in ["tinkoff-investments", "tinkoff", "tinkoff_investments"]:
    try:
        d = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{n}/json", timeout=30))
        print(f"OK   {n}: version={d['info']['version']} requires_python={d['info'].get('requires_python')}")
        print("     requires:", (d['info'].get('requires_dist') or [])[:8])
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} {n}")
    except Exception as e:
        print(f"ERR {n}: {e}")
