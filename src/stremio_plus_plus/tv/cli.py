"""`mise run tv -- pair | status | key KEY_X [...] | text "<string>"`"""

import argparse
import asyncio

from stremio_plus_plus.config.env import load_env
from stremio_plus_plus.tv.constants import TOKEN_FILE
from stremio_plus_plus.tv.remote import TvRefusedError, TvRemote


async def _run(args: argparse.Namespace) -> int:
    env = load_env()
    remote = TvRemote(str(env.tv_host), env.companion_data_dir / TOKEN_FILE)
    if args.cmd == "status":
        print(f"TV {env.tv_host}: {'paired' if remote.paired else 'not paired'}")  # noqa: T201  (CLI output)
        return 0 if remote.paired else 1
    try:
        if args.cmd == "pair":
            print(f"Connecting to the TV at {env.tv_host}: press Allow on the TV if it asks…")  # noqa: T201
            await remote.pair()
            print("Paired.")  # noqa: T201
        elif args.cmd == "key":
            await remote.keys(*args.keys)
        elif args.cmd == "text":
            await remote.text(args.text)
    except (TvRefusedError, OSError) as exc:
        print(f"TV control failed: {exc}")  # noqa: T201
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Control the Samsung TV from this host")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pair", help="pair this host with the TV (press Allow on the TV)")
    sub.add_parser("status", help="exit 0 if this host holds a pairing token")
    key = sub.add_parser("key", help="send remote keys, e.g. KEY_HOME KEY_DOWN KEY_ENTER")
    key.add_argument("keys", nargs="+")
    text = sub.add_parser("text", help="type into the focused on-screen keyboard")
    text.add_argument("text")
    raise SystemExit(asyncio.run(_run(parser.parse_args())))


if __name__ == "__main__":
    main()
