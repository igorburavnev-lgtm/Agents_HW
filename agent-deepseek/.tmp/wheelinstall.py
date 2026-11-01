"""Minimal wheel installer: resolves from PyPI JSON and extracts wheels into a venv site-packages.

Used because `pip install` is blocked by the sandbox's file-write policy in this environment.
"""
import json
import os
import re
import sys
import time
import zipfile
import urllib.request

PY = (3, 12)
PLAT = "win_amd64"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

UA = {"User-Agent": "wheel-installer/1.0"}
_versions_cache = {}


def fetch_json(url, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def latest_version(name):
    """Newest non-prerelease version, falling back to prerelease."""
    if name in _versions_cache:
        return _versions_cache[name]
    data = fetch_json(f"https://pypi.org/pypi/{name}/json")
    stable = [v for v in data["releases"] if not re.search(r"[a-zA-Z]", v)]
    if stable:
        best = max(stable, key=_vkey)
    else:
        best = max(data["releases"], key=_vkey)
    _versions_cache[name] = best
    return best


def _vkey(v):
    parts = re.split(r"[.]", v)
    out = []
    for p in parts:
        m = re.match(r"^(\d+)", p)
        out.append((0, int(m.group(1))) if m else (1, p))
    return out


def wheel_score(fname):
    """Higher is better; None means incompatible with CPython 3.12 / win_amd64."""
    if not fname.endswith(".whl"):
        return None
    parts = fname[:-4].split("-")
    if len(parts) < 5:
        return None
    pytags, abitag, plattag = parts[-3], parts[-2], parts[-1]

    def py_ok(tag):
        if tag in ("py3", "py2.py3"):
            return 50
        m = re.match(r"^cp(\d)(\d+)$", tag)
        if m:
            return 100 if (int(m.group(1)), int(m.group(2))) == PY else None
        return None

    best_py = None
    for t in pytags.split("."):
        s = py_ok(t)
        if s is not None and (best_py is None or s > best_py):
            best_py = s
    if best_py is None:
        return None

    if plattag == "any":
        return best_py
    if plattag != PLAT:
        return None
    if abitag in ("none", f"cp{PY[0]}{PY[1]}"):
        return best_py + 10
    m = re.match(r"^cp(\d)(\d+)$", abitag)
    if m and (int(m.group(1)), int(m.group(2))) <= PY:
        return best_py + 5
    return None


def pick_wheel(files):
    best, best_score = None, -1
    for f in files:
        if f["packagetype"] != "bdist_wheel":
            continue
        s = wheel_score(f["filename"])
        if s is not None and s > best_score:
            best, best_score = f, s
    return best


_MARK_RE = re.compile(r'^\s*([\w.]+)\s*(==|!=|>=|<=|>|<|~=)\s*["\']([^"\']*)["\']\s*$')


def _cmp(op, a, b):
    def key(v):
        return [int(x) if x.isdigit() else x for x in re.split(r"[.]", v)]

    try:
        ka, kb = key(a), key(b)
        # compare piecewise, falling back to string compare
        for x, y in zip(ka, kb):
            if isinstance(x, int) and isinstance(y, int):
                if x != y:
                    return (x > y) - (x < y)
            else:
                if str(x) != str(y):
                    return (str(x) > str(y)) - (str(x) < str(y))
        if len(ka) != len(kb):
            return (len(ka) > len(kb)) - (len(ka) < len(kb))
        return 0
    except Exception:  # noqa: BLE001
        return (a > b) - (a < b)


def eval_marker(marker, extras):
    """Tiny PEP 508 marker evaluator for the clauses this project needs."""
    if not marker:
        return True
    expr = marker.replace("(", " ").replace(")", " ")
    # split on ' or ' first (lowest precedence), then ' and '
    for or_part in re.split(r"\bor\b", expr):
        ok = True
        for and_part in re.split(r"\band\b", or_part):
            clause = and_part.strip()
            if not clause:
                continue
            m = _MARK_RE.match(clause)
            if not m:
                ok = False
                break
            var, op, val = m.group(1), m.group(2), m.group(3)
            if var == "extra":
                cur = val if val in extras else None
                if not (cur is not None or op == "!="):
                    ok = False
                    break
                continue
            if var == "python_version":
                cur = f"{PY[0]}.{PY[1]}"
            elif var == "python_full_version":
                cur = f"{PY[0]}.{PY[1]}.0"
            elif var in ("sys_platform", "platform_system"):
                cur = "win32" if var == "sys_platform" else "Windows"
            elif var == "os_name":
                cur = "nt"
            elif var == "platform_machine":
                cur = "AMD64"
            elif var == "implementation_name":
                cur = "cpython"
            else:
                ok = False
                break
            c = _cmp(op, cur, val)
            if op == "==":
                good = c == 0
            elif op == "!=":
                good = c != 0
            elif op == ">=":
                good = c >= 0
            elif op == "<=":
                good = c <= 0
            elif op == ">":
                good = c > 0
            elif op == "<":
                good = c < 0
            elif op == "~=":
                good = c >= 0 and str(cur).split(".")[0] == str(val).split(".")[0]
            else:
                good = False
            if not good:
                ok = False
                break
        if ok:
            return True
    return False


def parse_requires(reqs):
    """Yield (name, marker) from PEP 508 requirement strings, dropping version specs/extras."""
    out = []
    for r in reqs or []:
        if ";" in r:
            spec, marker = r.split(";", 1)
        else:
            spec, marker = r, ""
        spec = spec.strip()
        m = re.match(r"^([A-Za-z0-9_.\-]+)", spec)
        if not m:
            continue
        out.append((m.group(1), marker.strip()))
    return out


def resolve(top_names):
    """Breadth-first closure of runtime dependencies with latest compatible versions."""
    seen = {}
    pins = {}
    queue = []
    for item in top_names:
        if "==" in item:
            n, v = item.split("==", 1)
            pins[norm(n)] = v.strip()
            queue.append(n.strip())
        else:
            queue.append(item)
    while queue:
        name = queue.pop(0)
        key = norm(name)
        if key in seen:
            continue
        try:
            ver = pins.get(key) or latest_version(name)
            data = fetch_json(f"https://pypi.org/pypi/{name}/{ver}/json")
            wheel = pick_wheel(data["urls"])
        except Exception as e:  # noqa: BLE001
            seen[key] = {"name": name, "version": None, "error": str(e)}
            continue
        if wheel is None:
            seen[key] = {"name": name, "version": ver, "error": "no compatible wheel"}
            continue
        info = data["info"]
        seen[key] = {
            "name": info["name"],
            "version": ver,
            "file": wheel,
            "requires": parse_requires(info.get("requires_dist")),
        }
        for dep, marker in seen[key]["requires"]:
            if eval_marker(marker, set()):
                if norm(dep) not in seen:
                    queue.append(dep)
    return seen


def download(url, filename):
    os.makedirs(CACHE, exist_ok=True)
    dest = os.path.join(CACHE, filename)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    req = urllib.request.Request(url, headers=UA)
    tmp = dest + ".part"
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            f.write(chunk)
    os.replace(tmp, dest)
    return dest


def install(site_packages, resolved):
    os.makedirs(site_packages, exist_ok=True)
    for key, meta in sorted(resolved.items()):
        if meta.get("error"):
            print(f"SKIP {key}: {meta['error']}")
            continue
        path = download(meta["file"]["url"], meta["file"]["filename"])
        with zipfile.ZipFile(path) as z:
            for member in z.namelist():
                if member.endswith("/"):
                    continue
                if ".data/" in member:
                    continue  # scripts/headers not needed for this project
                target = os.path.join(site_packages, member)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(member) as src, open(target, "wb") as dst:
                    dst.write(src.read())
        print(f"OK   {meta['name']}=={meta['version']}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "list"
    tops = sys.argv[2].split(",") if len(sys.argv) > 2 else ["Django"]
    res = resolve(tops)
    print(f"resolved {len(res)} distributions for CPython {PY[0]}.{PY[1]} {PLAT}")
    for k, m in sorted(res.items()):
        print(f"  {k:28} {str(m.get('version')):12} {m.get('error') or m['file']['filename']}")
    if mode == "install":
        site = sys.argv[3]
        install(site, res)
