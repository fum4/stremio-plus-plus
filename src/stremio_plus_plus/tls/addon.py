"""Which certificate the addon's HTTPS listener uses.

ADDON_DOMAIN set (the owner): that domain's lego certificate, or no HTTPS until `tls:renew` ran;
never a silent switch to another name, which would break an installed addon URL. Unset (everyone
else): the streaming server's stremio.rocks certificate (stremio_cert.py).
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from stremio_plus_plus.tls import stremio_cert
from stremio_plus_plus.tls.paths import cert_paths

HttpsMode = Literal["own-domain", "stremio"]


@dataclass(frozen=True)
class AddonTls:
    mode: HttpsMode
    domain: str
    cert_path: Path
    key_path: Path
    stamp: int = 0  # the cert file's mtime: changes on renewal, so the listener reloads


def _addon_tls(mode: HttpsMode, domain: str, cert: Path, key: Path) -> AddonTls:
    return AddonTls(mode, domain, cert, key, cert.stat().st_mtime_ns)


async def resolve(
    addon_domain: str | None,
    lego_dir: Path,
    server_data_dir: Path,
    stremio_out_dir: Path,
    renew: Callable[[], Awaitable[None]],
) -> AddonTls | None:
    if addon_domain:
        cert, key = cert_paths(lego_dir, addon_domain)
        ok = cert.is_file() and key.is_file()
        return _addon_tls("own-domain", addon_domain, cert, key) if ok else None
    found = await stremio_cert.ensure(server_data_dir, stremio_out_dir, renew)
    if found is None:
        return None
    return _addon_tls("stremio", found.domain, found.cert_path, found.key_path)
