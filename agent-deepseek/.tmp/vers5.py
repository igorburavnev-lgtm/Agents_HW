import json, re, urllib.request
def latest(name):
    d = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=30))
    vs = [v for v in d["releases"] if not re.search(r"[a-zA-Z]", v)]
    vs.sort(key=lambda v: [int(x) for x in re.split(r"[.]", v)])
    print(f"{name:14} {vs[-1]}")
for n in ["black","isort","coverage","gunicorn"]:
    try: latest(n)
    except Exception as e: print(n,"ERR",e)
