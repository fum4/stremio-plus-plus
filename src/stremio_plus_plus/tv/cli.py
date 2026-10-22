"""`mise run tv -- pair | status | key KEY [...] | text "<string>"` for the TV_OS in config.

Keys: the common names in keys.COMMON_KEYS (HOME, BACK, UP, ENTER, PLAY_PAUSE…) or the OS's
native names (KEY_HOME on Samsung, HOME on webOS, KEYCODE_HOME on Android TV / Fire TV).
"""

import argparse
import asyncio

from stremio_plus_plus.config.env import load_env
from stremio_plus_plus.config.host import tv_target
from stremio_plus_plus.config.settings_file import SettingsFile
from stremio_plus_plus.tv.base import TvControlError
from stremio_plus_plus.tv.factory import PAIR_HINT, make_remote
from stremio_plus_plus.tv.keys import COMMON_KEYS


async def _ask_code() -> str:
    return await asyncio.to_thread(input, "Code shown on the TV: ")


async def _run(args: argparse.Namespace) -> int:
    env = load_env()
    target = tv_target(env, SettingsFile(env.config_dir).settings)
    try:
        remote = make_remote(target, env.companion_data_dir)
    except TvControlError as exc:
        print(exc)  # noqa: T201
        return 1
    assert target is not None  # make_remote checked it
    tv = f"TV {target[0]} ({target[1]})"
    if args.cmd == "status":
        print(f"{tv}: {'paired' if remote.paired else 'not paired'}")  # noqa: T201  (CLI output)
        return 0 if remote.paired else 1
    try:
        if args.cmd == "pair":
            print(f"Connecting to the {tv}: {PAIR_HINT[target[1]]}…")  # noqa: T201
            await remote.pair(_ask_code)
            print("Paired.")  # noqa: T201
        elif args.cmd == "key":
            await remote.keys(*args.keys)
        elif args.cmd == "text":
            await remote.text(args.text)
    except (TvControlError, OSError) as exc:
        print(f"TV control failed: {exc}")  # noqa: T201
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Control the TV (TV_OS, TV_HOST) from this host")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pair", help="pair this host with the TV (confirm on the TV / type its code)")
    sub.add_parser("status", help="exit 0 if this host holds pairing credentials")
    key = sub.add_parser("key", help=f"send remote keys: {' '.join(COMMON_KEYS)}, or native names")
    key.add_argument("keys", nargs="+")
    text = sub.add_parser("text", help="type into the focused on-screen keyboard")
    text.add_argument("text")
    raise SystemExit(asyncio.run(_run(parser.parse_args())))


if __name__ == "__main__":
    main()
