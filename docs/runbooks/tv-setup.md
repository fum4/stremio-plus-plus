# TV setup — point the Samsung TV at Batman, and back

**Invariant:** the TV must always be revertible in one setting. Record the current value **before** changing anything.

## Recorded values
| What | Value | Recorded |
|---|---|---|
| TV model code / software version | _pending — owner_ | |
| TV's original **Settings → Streaming → server URL** | _pending — owner_ | |
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
