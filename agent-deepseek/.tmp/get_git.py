"""Download PortableGit and self-extract it (git is not installed on this machine)."""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

AD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(AD, ".tmp")
DEST = os.path.join(TMP, "git")
EXE = os.path.join(TMP, "PortableGit.7z.exe")


def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "setup/1.0"})
    return urllib.request.urlopen(req, timeout=60)


def main():
    os.makedirs(TMP, exist_ok=True)
    if os.path.exists(os.path.join(DEST, "cmd", "git.exe")):
        print("git already extracted")
        return 0
    print("querying GitHub releases...", flush=True)
    data = json.load(fetch("https://api.github.com/repos/git-for-windows/git/releases/latest",
                           {"User-Agent": "setup/1.0", "Accept": "application/vnd.github+json"}))
    asset = None
    for a in data["assets"]:
        if re.match(r"^PortableGit-.*-64-bit\.7z\.exe$", a["name"]):
            asset = a
            break
    if not asset:
        print("no PortableGit asset found", [a["name"] for a in data["assets"]][:10])
        return 1
    print(f"asset: {asset['name']} size={asset['size']/1e6:.1f} MB", flush=True)

    if not os.path.exists(EXE) or os.path.getsize(EXE) != asset["size"]:
        r = fetch(asset["browser_download_url"])
        done = 0
        t0 = time.time()
        with open(EXE + ".part", "wb") as f:
            while True:
                chunk = r.read(262144)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if done % (10 * 1024 * 1024) < 262144:
                    print(f"  {done/1e6:.1f} MB ({done/1e6/(time.time()-t0):.2f} MB/s)", flush=True)
        os.replace(EXE + ".part", EXE)
        print(f"downloaded {done} bytes", flush=True)

    print("extracting...", flush=True)
    p = subprocess.run([EXE, "-y", f"-o{DEST}"], capture_output=True, text=True)
    print("extract exit:", p.returncode)
    if p.stdout:
        print(p.stdout[-500:])
    if p.stderr:
        print("stderr:", p.stderr[-500:])
    git = os.path.join(DEST, "cmd", "git.exe")
    print("git present:", os.path.exists(git))
    if os.path.exists(git):
        v = subprocess.run([git, "--version"], capture_output=True, text=True)
        print(v.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
