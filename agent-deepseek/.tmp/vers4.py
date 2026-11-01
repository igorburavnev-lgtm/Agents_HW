import urllib.request, urllib.error
def probe(url):
    try:
        r = urllib.request.urlopen(url, timeout=25)
        body = r.read(300)
        print(f"OK   {r.status} {url}\n     {body[:160]!r}")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} {url}")
    except Exception as e:
        print(f"ERR  {url} -> {type(e).__name__}: {e}")

probe("https://pypi.org/simple/django/")            # sanity check
probe("https://pypi.org/simple/tinkoff-investments/")
probe("https://pypi.org/simple/tinkoff/")
probe("https://pypi.org/pypi/plotly/json")          # sanity check on JSON api
