"""Where lego keeps the certificate for ADDON_DOMAIN (`lego --path <tls_dir>`)."""

from pathlib import Path


def cert_paths(tls_dir: Path, domain: str) -> tuple[Path, Path]:
    certs = tls_dir / "certificates"
    return certs / f"{domain}.crt", certs / f"{domain}.key"
