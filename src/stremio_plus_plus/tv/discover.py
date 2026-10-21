"""Find TVs on the LAN (SSDP), so the setup can offer them instead of asking for an IP.

Every TV OS we support answers DIAL (the cast protocol), Samsung and LG also their own device
types. The device description (UPnP XML at LOCATION) names the manufacturer, which picks the OS.
"""

import asyncio
import re
import socket
from dataclasses import dataclass
from ipaddress import IPv4Address
from urllib.parse import urlparse

import httpx

from stremio_plus_plus.config.settings import TvOs

SSDP_ADDR = ("239.255.255.250", 1900)
SEARCH_TARGETS = (
    "urn:dial-multiscreen-org:service:dial:1",
    "urn:samsung.com:device:RemoteControlReceiver:1",
    "urn:lge-com:service:webos-second-screen:1",
)
DESCRIPTION_TIMEOUT_S = 2.0
# Android TV is licensed to many brands; these ship it (Sony, Philips, TCL, Xiaomi, NVIDIA Shield…).
ANDROID_BRANDS = ("sony", "philips", "tcl", "xiaomi", "nvidia", "google", "sharp", "toshiba")


@dataclass(frozen=True)
class FoundTv:
    host: IPv4Address
    name: str
    model: str
    manufacturer: str
    os: TvOs | None  # None: a TV we found but can't control


def _search(st: str) -> bytes:
    return (
        "M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {SSDP_ADDR[0]}:{SSDP_ADDR[1]}\r\n"
        'MAN: "ssdp:discover"\r\nMX: 2\r\n'
        f"ST: {st}\r\n\r\n"
    ).encode()


def parse_response(data: bytes) -> dict[str, str]:
    lines = data.decode(errors="replace").split("\r\n")
    return {
        k.strip().lower(): v.strip() for k, sep, v in (line.partition(":") for line in lines) if sep
    }


def _tag(xml: str, tag: str) -> str:
    m = re.search(rf"<{tag}>([^<]*)</{tag}>", xml)
    return m.group(1).strip() if m else ""


def classify(manufacturer: str, model: str, server: str) -> TvOs | None:
    text = f"{manufacturer} {model} {server}".lower()
    if "eureka" in text:  # a cast-only Chromecast: answers DIAL, runs no apps
        return None
    if "samsung" in text:
        return "samsung"
    if "lg electronics" in text or "webos" in text or manufacturer.lower() == "lg":
        return "webos"
    if "amazon" in text or "aft" in model.lower():
        return "firetv"
    if "android" in text or any(b in text for b in ANDROID_BRANDS):
        return "androidtv"
    return None


class _Collector(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.replies: dict[str, dict[str, str]] = {}

    def datagram_received(self, data: bytes, addr: tuple[str | object, int]) -> None:
        headers = parse_response(data)
        if "location" in headers and isinstance(addr[0], str):
            self.replies.setdefault(addr[0], headers)


async def _describe(http: httpx.AsyncClient, ip: str, headers: dict[str, str]) -> FoundTv | None:
    location = headers["location"]
    if urlparse(location).hostname != ip:  # only trust a description served by the device itself
        return None
    try:
        xml = (await http.get(location, timeout=DESCRIPTION_TIMEOUT_S)).text
    except httpx.HTTPError:
        xml = ""
    manufacturer, model = _tag(xml, "manufacturer"), _tag(xml, "modelName")
    name = _tag(xml, "friendlyName") or model or ip
    os_ = classify(manufacturer, model, headers.get("server", ""))
    return FoundTv(IPv4Address(ip), name, model, manufacturer, os_)


async def discover(seconds: float = 3.0) -> list[FoundTv]:
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.bind(("", 0))
    transport, collector = await loop.create_datagram_endpoint(_Collector, sock=sock)
    try:
        for _ in range(2):  # UDP: ask twice
            for st in SEARCH_TARGETS:
                transport.sendto(_search(st), SSDP_ADDR)
            await asyncio.sleep(seconds / 2)
    finally:
        transport.close()
    async with httpx.AsyncClient() as http:
        found = await asyncio.gather(
            *(_describe(http, ip, headers) for ip, headers in collector.replies.items())
        )
    tvs = [tv for tv in found if tv is not None]
    return sorted(tvs, key=lambda tv: (tv.os is None, tv.name))
