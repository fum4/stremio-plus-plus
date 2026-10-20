"""Every 15 s: per engine, session download + speed + progress of every file the TV has requested."""
import json, re, subprocess, time, urllib.request
from pathlib import Path

LOG = Path.home() / "Library/Logs/stremio-companion/server.log"
BASE = "http://127.0.0.1:11470"

def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=5) as r:
            return json.load(r)
    except Exception:
        return None

def requested_files():
    tail = subprocess.run(["tail", "-n", "3000", str(LOG)], capture_output=True, text=True).stdout
    return sorted(set(re.findall(r"^-> GET /([0-9a-f]{40})/(\d+) ", tail, re.M)))

while True:
    engines = get("/stats.json") or {}
    conns = subprocess.run("netstat -anp tcp | grep 192.168.1.134 | grep -c ESTABLISHED",
                           shell=True, capture_output=True, text=True).stdout.strip()
    free = subprocess.run("df -g ~ | awk 'NR==2{print $4}'", shell=True, capture_output=True, text=True).stdout.strip()
    parts = [time.strftime("%H:%M:%S"), f"engines={len(engines)}", f"tv_conns={conns}", f"free={free}G"]
    for ih, idx in requested_files():
        if ih not in engines:
            parts.append(f"{ih[:6]}/{idx}:gone"); continue
        s = get(f"/{ih}/{idx}/stats.json") or {}
        parts.append(f"{ih[:6]}/{idx}: dl={(s.get('downloaded') or 0)/1e6:.0f}MB "
                     f"{(s.get('downloadSpeed') or 0)/1e6:.1f}MB/s prog={s.get('streamProgress') or 0:.3f} peers={s.get('peers')}")
    print(" | ".join(parts), flush=True)
    time.sleep(15)
