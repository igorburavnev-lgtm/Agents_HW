import json, re, urllib.request
def vers(name):
    d = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=30))
    return [v for v in d["releases"] if not re.search(r"[a-zA-Z]", v)]
def top(name, prefix, n=3):
    vs = [v for v in vers(name) if v.startswith(prefix)]
    vs.sort(key=lambda v: [int(x) for x in v.split(".")])
    print(f"{name:26} {prefix}* -> {vs[-n:]}")
for name, pre in [("Django","5.2."),("plotly","6."),("redis","6."),("celery","5.5."),("djangorestframework","3.16."),("django-filter","25."),("django-crispy-forms","2.4"),("crispy-bootstrap3","2024")]:
    try: top(name, pre)
    except Exception as e: print(name, "ERR", e)
