"""What this host is, resolved once at boot: its LAN IP and the addon's secret token.

The owner pins both in the environment (.env.local, repo-secrets); a fresh install detects the IP
and generates the token once into secrets.toml, so nothing has to be typed before the setup UI.
"""

import secrets
import socket
from ipaddress import IPv4Address

from stremio_plus_plus.config.env import Env
from stremio_plus_plus.config.settings_file import SettingsFile

TOKEN_BYTES = 24  # 32 url-safe characters
# Any routable address: connect() on a UDP socket only picks the outgoing interface, sends nothing.
ROUTE_PROBE = ("192.0.2.1", 9)


class HostError(RuntimeError):
    pass


def detect_lan_ip() -> IPv4Address | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(ROUTE_PROBE)
            ip = IPv4Address(s.getsockname()[0])
    except OSError:
        return None
    return ip if ip.is_private and not ip.is_loopback else None


def lan_ip(env: Env) -> IPv4Address:
    ip = env.host_lan_ip or detect_lan_ip()
    if ip is None:
        raise HostError("no LAN address found: connect to the network or set HOST_LAN_IP")
    return ip


def addon_token(env: Env, settings_file: SettingsFile) -> str:
    if env.addon_token:
        return env.addon_token
    if token := settings_file.secrets.addon_token:
        return token
    token = secrets.token_urlsafe(TOKEN_BYTES)
    settings_file.set_secret("addon_token", token)
    return token
