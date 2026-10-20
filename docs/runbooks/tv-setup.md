# TV setup — point the Samsung TV at Batman, and back

**Invariant:** the TV must always be revertible in one setting. Record the current value **before** changing anything.

## Recorded values
| What | Value | Recorded |
|---|---|---|
| TV model code / software version | `UE43TU7092UXXH` (Samsung 2020 TU7000, 43") · `T-KTSU2DEUC-2743.0` · Tizen 5.5 | 2026-10-21 |
| Stremio TV app | **Stremio Theater v1.12.1**, platform tizen | 2026-10-21 |
| TV's original **Settings → Streaming → server URL** | **`http://127.0.0.1:11470`** (on-TV server, v4.20.8) — **the revert value** | 2026-10-21 |
| Batman Wi-Fi MAC | `84:2f:57:91:27:e5` | 2026-10-21 |
| Batman LAN IP (DHCP reservation) | _pending — currently `192.168.1.132`, not reserved_ | |
| Router | `192.168.1.1` | 2026-10-21 |

## 1. Give Batman a fixed LAN IP
On the router (`http://192.168.1.1`): DHCP / LAN settings → address reservation → MAC `84:2f:57:91:27:e5` → the IP above. Confirm with `ipconfig getifaddr en0` after a Wi-Fi reconnect. macOS **Private Wi-Fi address** must be **Off** for the home network (System Settings → Wi-Fi → (i) on the network), or the MAC rotates and the reservation misses.

## 2. Start the server on Batman
`mise run install-service` (see README). Check: `curl -s http://<batman-ip>:11470/stats.json` from another device on the LAN.

## 3. Point the TV at Batman
In the Stremio TV app: **Settings → Streaming → Streaming server URL** → write down the current value in the table above → set `http://<batman-ip>:11470` → confirm the app shows the server as online. _Exact menu labels: confirm in phase 0 and fix here._

## 4. Revert (Batman asleep, away, or broken)
Settings → Streaming → server URL → the original value from the table. _Confirm in phase 0 that this is the only step._

## Batman sleep
- Torrent playback on the TV needs Batman awake, on power, on the LAN.
- During a film: `caffeinate -dimsu` in a terminal, or System Settings → Battery → Options → "Prevent automatic sleeping on power adapter when the display is off".
- Lid closed: sleeps unless on power with an external display (clamshell). _Phase 0 records what the TV shows when Batman sleeps mid-film._

## TV codec support (UE43TU7092, 2020 TU7000, Tizen 5.5)
From Samsung's published 2020 TU-series specs, **not yet verified on this set**: phase 0 plays one sample of each.

| | Expected | Matters because |
|---|---|---|
| H.264, HEVC (4K60 10-bit), VP9 | ✅ | most torrents |
| AV1 | likely ✅ (Samsung added AV1 in 2020 models) | some newer web releases |
| HDR10 / HDR10+ / HLG | ✅ | |
| **Dolby Vision** | ❌ (Samsung never supports DV) | DV-only (profile 5) files show wrong colours; DV P7/P8 fall back to the HDR10 base layer |
| AC3 / E-AC3 (DD+) | ✅ | |
| **DTS / DTS-HD, TrueHD** | ❌ (no DTS on 2018–2021 Samsung TVs) | common in remuxes → silent or no playback unless the server transcodes audio |

The TV can't transcode. The streaming server on Batman can (ffmpeg 9 + VideoToolbox, `/hlsv2`). Phase 0 checks whether Theater falls back to the server's transcode for DTS.
