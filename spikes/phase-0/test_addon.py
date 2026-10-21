"""Phase-0 throwaway: a plain-http Stremio subtitles addon that logs every request."""
import json, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

HOST_IP, PORT = sys.argv[1], int(sys.argv[2])
MANIFEST = {
    "id": "io.github.fum4.stremio-companion.phase0", "version": "0.0.1",
    "name": "Companion phase-0 test", "description": "Plain-http subtitle test (temporary)",
    "resources": ["subtitles"], "types": ["movie", "series"], "idPrefixes": ["tt", "kitsu"],
    "catalogs": [],
}

def srt() -> bytes:
    out = []
    for i in range(1, 1441):  # one cue every 5 s for 2 h
        s = (i - 1) * 5
        ts = lambda t: f"{t//3600:02}:{t%3600//60:02}:{t%60:02},000"
        out.append(f"{i}\n{ts(s)} --> {ts(s+4)}\nCOMPANION TEST · plain http · {ts(s)[:8]}\n")
    return "\n".join(out).encode()

SRT = srt()

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body, ctype):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*"); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        print(json.dumps({"t": time.strftime("%H:%M:%S"), "ip": self.client_address[0], "path": unquote(self.path),
                          "ua": self.headers.get("User-Agent")}), flush=True)
        if self.path == "/manifest.json":
            return self.send(200, json.dumps(MANIFEST).encode(), "application/json")
        if self.path.startswith("/subtitles/"):
            body = {"subtitles": [{"id": "companion-phase0", "lang": "ron",
                                   "url": f"http://{HOST_IP}:{PORT}/test.srt"}]}
            return self.send(200, json.dumps(body).encode(), "application/json")
        if self.path.startswith("/test.srt"):
            return self.send(200, SRT, "application/x-subrip; charset=utf-8")
        self.send(404, b"{}", "application/json")

ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
