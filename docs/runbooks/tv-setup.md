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

## 3. Point the TV at the Mac (HTTPS only)
The TV app **refuses plain http to anything but `127.0.0.1`**: `http://<mac-ip>:11470` shows "offline" and never reaches the Mac. The server's HTTPS mode solves it: `remoteHttps` = the LAN IP gives a public DNS name that resolves to the LAN IP, with a certificate issued by Stremio's API.
1. Write down the current server URL on the TV (table above) if it isn't recorded yet.
2. TV: Stremio → **Settings → Streaming → server URL** → the URL `mise run host:doctor` prints, e.g. `https://192-168-1-132.519b6502d940.stremio.rocks:12470` → it shows **online**.

A new Mac IP means a new hostname: re-run `mise run server:configure` and re-enter the URL. Needs working internet DNS. A router that blocks public names resolving to private IPs (DNS-rebind protection) would break it; this router is fine (verified 2026-10-21).

## 4. Revert
TV: Stremio → Settings → Streaming → server URL → **`http://127.0.0.1:11470`**. That's the only step: the TV goes back to its own server, and playback works with the Mac off. _(One-setting revert: confirm on the TV on the next occasion and tick this.)_

## 5. Install the "Romanian (AI)" addon
The TV app has no "add addon by URL" field; addons come from your Stremio account.
1. The addon needs an HTTPS address. Until `nomadware.io` is set up: `mise run addon:tunnel` on the Mac prints `https://<random>.trycloudflare.com` (a new one every run).
2. Stremio desktop app (same account) → **Addons** → paste `<https address>/manifest.json` into the search box → **Install**. If an older "Romanian (AI)" / "Companion" addon is listed, uninstall it first.
3. TV: Stremio → Settings → **Sync addons**. The track appears in the subtitles menu as **Romanian (AI)** (language Romanian).

## 6. TV control from the host
Each host pairs with the TV once (`mise run host:promote` does it; manually: `mise run tv -- pair`, then press **Allow** on the TV). The token is stored on the host (`<data dir>/tv-token`, mode 600), never in git; a new host pairs itself. Then:
- `mise run tv -- text '<string>'` types into the focused on-screen keyboard (server URL, addon search…).
- `mise run tv -- key KEY_HOME KEY_DOWN KEY_ENTER …` sends remote keys.
- Revoke: TV Settings → General → External Device Manager → Device Connection Manager → Device List → remove *stremio-companion*.

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
