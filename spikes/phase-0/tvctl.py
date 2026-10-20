"""Scratch TV remote over the Samsung WS API: pair | key KEY_X ... | text "<string>" """
import base64, json, ssl, sys, time
from pathlib import Path
import websocket

HOST, NAME = "192.168.1.134", base64.b64encode(b"stremio-companion").decode()
TOKEN = Path("/tmp/stremio-companion-tvctl/token")

def connect():
    tok = TOKEN.read_text().strip() if TOKEN.exists() else ""
    url = f"wss://{HOST}:8002/api/v2/channels/samsung.remote.control?name={NAME}" + (f"&token={tok}" if tok else "")
    ws = websocket.create_connection(url, sslopt={"cert_reqs": ssl.CERT_NONE}, timeout=60)
    deadline = time.time() + 60
    while time.time() < deadline:
        ev = json.loads(ws.recv())
        if ev.get("event") == "ms.channel.connect":
            t = ev.get("data", {}).get("token")
            if t: TOKEN.write_text(t)
            return ws
        if ev.get("event") == "ms.channel.unauthorized":
            sys.exit("TV refused (Deny pressed?)")
        print("skip event:", ev.get("event"), flush=True)
    sys.exit("no Allow within 60 s")

def remote(ws, params):
    ws.send(json.dumps({"method": "ms.remote.control", "params": params}))

cmd, args = sys.argv[1], sys.argv[2:]
ws = connect()
if cmd == "pair":
    print("paired; token saved" if TOKEN.exists() else "connected (no token issued)")
elif cmd == "key":
    for k in args:
        remote(ws, {"Cmd": "Click", "DataOfCmd": k, "Option": "false", "TypeOfRemote": "SendRemoteKey"}); time.sleep(0.4)
    print("sent", args)
elif cmd == "text":
    remote(ws, {"Cmd": base64.b64encode(args[0].encode()).decode(), "DataOfCmd": "base64", "TypeOfRemote": "SendInputString"})
    time.sleep(0.5); remote(ws, {"TypeOfRemote": "SendInputEnd"})
    print("typed", len(args[0]), "chars")
time.sleep(0.5); ws.close()
