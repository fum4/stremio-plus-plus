# TV setup — point the Samsung TV at the Mac, install the addon, and revert

**Invariant:** the TV must always be revertible in one setting. Record the current value **before** changing anything.

## Recorded values
| What | Value | Recorded |
|---|---|---|
| TV model code / software version | `UE43TU7092UXXH` (Samsung 2020 TU7000, 43") · `T-KTSU2DEUC-2743.0` · Tizen 5.5 | 2026-10-21 |
| Stremio TV app | **Stremio Theater v1.12.1**, platform tizen (closed source, not stremio-web) | 2026-10-21 |
| TV's original **Settings → Streaming → server URL** | **`http://127.0.0.1:11470`** (the TV's own server, v4.20.8) — **the revert value** | 2026-10-21 |
| Batman Wi-Fi MAC the router sees | `22:3c:5b:52:a1:8f` (macOS private address, *Fixed*; hardware MAC `84:2f:57:91:27:e5` is not used on this network) | 2026-10-21 |
| Batman LAN IP | `192.168.1.132` — _DHCP reservation pending_ | 2026-10-21 |
| Router | `192.168.1.1` | 2026-10-21 |
| TV LAN IP / Wi-Fi MAC | `192.168.1.134` / `d0:c2:4e:13:e0:49` — _DHCP reservation pending_ | 2026-10-21 |

## 1. Give the Mac a fixed LAN IP
The TV's server URL contains the Mac's IP, so it must never change.
1. Mac: System Settings → Wi-Fi → (i) next to the home network → **Private Wi-Fi address: Fixed** (or Off). Not *Rotating*: that changes the MAC and breaks the reservation.
2. Read the MAC the router will see: `ifconfig en0 | awk '/ether/{print $2}'`.
3. Router (`http://192.168.1.1`): DHCP / LAN → **Address Reservation** (a.k.a. Static Lease) → that MAC → the IP → save.
4. Put the IP in `.env.local` as `HOST_LAN_IP=…`; `mise run host:doctor` confirms it matches.

## 2. Start the services on the Mac
`mise run host:promote` on a new Mac, or `mise run services:install`. `mise run host:doctor` must be all green; it prints the **TV server URL**.

## Automation (setup wizard, Your TV step)
The setup UI does §3 for you where it can: it finds the TV on the network (SSDP), pairs with it (the TV asks to **Allow**; Android TV shows a code), and **Type it for me** types the server URL into the focused field. The step ticks itself once the TV's first request reaches the server (untagged requests in `server.log`, `watch/clients.py`). **Set it up on my TV** (open Stremio → Settings → Streaming → Server URL by itself) needs a key sequence recorded on that TV model (`tv/macros.py`, `SET_SERVER_URL`); until then it isn't offered. The revert (§4) has the same **Type it for me**. The TV it controls is `config.toml` `[tv]` (`TV_HOST`/`TV_OS` in `.env.local` win).

## 3. Point the TV at the Mac (HTTPS only)
The TV app **refuses plain http to anything but `127.0.0.1`**: `http://<mac-ip>:11470` shows "offline" and never reaches the Mac. The server's HTTPS mode solves it: `remoteHttps` = the LAN IP gives a public DNS name that resolves to the LAN IP, with a certificate issued by Stremio's API.
1. Write down the current server URL on the TV (table above) if it isn't recorded yet.
2. TV: Stremio → **Settings → Streaming → server URL** → the URL `mise run host:doctor` prints, e.g. `https://192-168-1-132.519b6502d940.stremio.rocks:12470` → it shows **online**.

A new Mac IP means a new hostname: re-run `mise run server:configure` and re-enter the URL. Needs working internet DNS. A router that blocks public names resolving to private IPs (DNS-rebind protection) would break it; this router is fine (verified 2026-10-21).

## 4. Revert
TV: Stremio → Settings → Streaming → server URL → **`http://127.0.0.1:11470`**. That's the only step: the TV goes back to its own server, and playback works with the Mac off. _(One-setting revert: confirm on the TV on the next occasion and tick this.)_

## 5. Install the "Stremio++" addon
The TV app has no "add addon by URL" field; addons come from your Stremio account. Install **once**: the address never changes.
1. On the Mac: `mise run addon:url` prints `https://stremio.nomadware.io:8443/<secret>/manifest.json`. The secret keeps strangers out; don't share the URL.
2. Stremio desktop app (same account) → **Addons** → paste the URL into the search box → **Install**. Uninstall any older "Romanian (AI)" / "Companion" addon first (the addon was called "Romanian (AI)" before v0.2.0; same id, so reinstalling replaces it).
3. TV: Stremio → Settings → **Sync addons**. The addon is listed as **Stremio++**; its track shows in the subtitles menu as **Romanian (AI)** (language Romanian).

How it reaches the Mac: `stremio.nomadware.io` is a public DNS name for the Mac's **LAN** IP (Nomadware.io `infra/terraform/records.tf`), so only devices at home reach it; the certificate is a real Let's Encrypt one, renewed weekly. The HTTPS port serves nothing but the token-protected addon.

## 6. TV control from the host
`TV_OS` in `infra/env/companion.env` picks the adapter (`src/stremio_plus_plus/tv/`); `TV_HOST` is the TV's IP. Each host pairs once (`mise run host:promote` does it; manually: `mise run tv -- pair`). Credentials stay on the host under `<data dir>/`, mode 600, never in git; a new host pairs itself. Protocol details and sources: [docs/research/tv-remote-protocols.md](../research/tv-remote-protocols.md).

| `TV_OS` | Verified on a real TV | Before pairing (TV side) | Pairing gesture | Credential file | Revoke on the TV |
|---|---|---|---|---|---|
| `samsung` (this TV) | ✅ UE43TU7092, Tizen 5.5 | nothing | press **Allow** | `tv-token` | Settings → General → External Device Manager → Device Connection Manager → Device List → remove *stremio++* |
| `webos` (LG) | ❌ untested | nothing (TV on, same LAN) | accept the **"allow this device"** prompt within a minute | `tv-webos-client-key` | _unverified:_ no per-device list is documented; a factory reset clears all paired clients |
| `androidtv` (Google TV, Sony, Philips, TCL, Shield…) | ❌ untested | nothing (the *Android TV Remote Service* is preinstalled) | type the **6-character code** the TV shows at the `Code shown on the TV:` prompt | `tv-androidtv-cert.pem`, `tv-androidtv-key.pem` | _unverified:_ Settings → Apps → *Android TV Remote Service* → Clear data (forgets all paired remotes) |
| `firetv` (Fire OS) | ❌ untested | Settings → My Fire TV → Developer options → **ADB debugging ON** (unlock Developer options: About → click the device name 7×). **Record this as a TV change; revert = ADB debugging OFF** | tick **Always allow from this computer**, press OK | `tv-firetv-adbkey` (+ `.pub`) | Developer options → ADB debugging OFF (or *Revoke USB debugging authorisations*) |

Then:
- `mise run tv -- text '<string>'` types into the focused on-screen keyboard (server URL, addon search…). Fire TV: printable ASCII only.
- `mise run tv -- key HOME DOWN ENTER …` sends remote keys. Common names on every OS: `HOME BACK UP DOWN LEFT RIGHT ENTER PLAY PAUSE PLAY_PAUSE STOP REWIND FAST_FORWARD VOLUME_UP VOLUME_DOWN MUTE MENU INFO` (Samsung and webOS have no `PLAY_PAUSE` toggle: use `PLAY`/`PAUSE`). Any other name is sent as the OS's native key (`KEY_HOME` on Samsung, `HOME` on webOS, `KEYCODE_HOME` on Android TV / Fire TV), so existing `KEY_…` scripts keep working.
- `mise run tv -- status` exits 0 if this host holds credentials (no network check); `host:doctor` also checks the TV's control port for `TV_OS`.

The TV is at `TV_HOST` (`infra/env/companion.env`); give it a DHCP reservation too (Wi-Fi MAC `d0:c2:4e:13:e0:49`).

## When the Mac sleeps
- Torrent playback through the Mac needs it awake, on power, on the LAN. Asleep → the TV can't play torrents until you wake it or [revert](#4-revert).
- During a film: `caffeinate -dimsu` in a terminal, or System Settings → Battery → Options → "Prevent automatic sleeping on power adapter when the display is off".
- Lid closed: sleeps unless on power with an external display (clamshell). _Not yet observed what the TV shows when the Mac sleeps mid-film._

## TV codec support (UE43TU7092, 2020 TU7000, Tizen 5.5)
From Samsung's published 2020 TU-series specs; HEVC 10-bit 4K + E-AC-3 5.1 verified on this set (MobLand, 2026-10-21), the rest not yet.

| | Expected | Matters because |
|---|---|---|
| H.264, HEVC (4K60 10-bit), VP9 | ✅ | most torrents |
| AV1 | likely ✅ (Samsung added AV1 in 2020 models) | some newer web releases |
| HDR10 / HDR10+ / HLG | ✅ | |
| **Dolby Vision** | ❌ (Samsung never supports DV) | DV-only (profile 5) files show wrong colours; DV P7/P8 fall back to the HDR10 base layer |
| AC3 / E-AC3 (DD+) | ✅ | |
| **DTS / DTS-HD, TrueHD** | ❌ (no DTS on 2018–2021 Samsung TVs) | common in remuxes → silent or no playback unless the server transcodes audio |

The TV can't transcode. The server on the Mac can (ffmpeg; VideoToolbox for audio only, its video self-test fails on Batman). Whether Theater falls back to the server's transcode for DTS: _not yet tested_.
