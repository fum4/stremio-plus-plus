"""Changes to the user's addon collection that never lose anything: put ours first, install it,
or point it at a new URL. Every other addon is kept exactly as Stremio returned it, in order.

Stremio lists streams in collection order, so first = Stremio++'s streams on top.
"""

from typing import Any, cast

Addon = dict[str, Any]


def _manifest(addon: Addon) -> dict[str, Any]:
    manifest = addon.get("manifest")
    return cast(dict[str, Any], manifest) if isinstance(manifest, dict) else {}


def addon_id(addon: Addon) -> str | None:
    value = _manifest(addon).get("id")
    return str(value) if value else None


def addon_name(addon: Addon) -> str:
    return str(_manifest(addon).get("name") or addon_id(addon) or "?")


def descriptor(transport_url: str, manifest: dict[str, Any]) -> Addon:
    return {"transportUrl": transport_url, "transportName": "", "manifest": manifest, "flags": {}}


def ours_first(addons: list[Addon], our_id: str, replace_with: Addon | None = None) -> list[Addon]:
    """The collection with our addon at index 0 (replaced by `replace_with` if given, added if
    missing and given); duplicates of ours collapse to one."""
    mine = [a for a in addons if addon_id(a) == our_id]
    others = [a for a in addons if addon_id(a) != our_id]
    first = replace_with or (mine[0] if mine else None)
    return ([first] if first is not None else []) + others


def position(addons: list[Addon], our_id: str) -> int | None:
    return next((i for i, a in enumerate(addons) if addon_id(a) == our_id), None)
