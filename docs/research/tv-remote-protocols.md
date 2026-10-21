# TV remote-control protocols (for `src/stremio_plus_plus/tv/`)

Researched 2026-10-21. Why: the host types the server URL during setup and will re-select the subtitle track during playback (key sequences), so it needs pair / keys / text on every TV OS that runs the official Stremio app. `TV_OS` (`infra/env/companion.env`) selects the adapter.

**Only Samsung is verified on a real TV** (the owner's UE43TU7092, Tizen 5.5). The other three adapters are built from the open-source clients below and tested hermetically (fake clients, no network); nobody has run them against hardware yet.

## Where the official Stremio app runs

| TV OS | Official Stremio app? | Adapter |
|---|---|---|
| Samsung Tizen | ✅ Samsung Apps ("Stremio Theater"); help centre says 2021+ models, third-party guides 2019+; runs on the owner's 2020 set | `samsung` |
| LG webOS | ✅ LG Content Store, 2020+ models (Stremio blog, 2024-04-30) | `webos` |
| Android TV / Google TV | ✅ Google Play, Android TV 5.0+ (Sony, Philips, TCL, Hisense-Android, Nvidia Shield, Chromecast with Google TV, Google TV Streamer) | `androidtv` |
| Amazon Fire TV (Fire OS) | ✅ Amazon Appstore since Dec 2025 (before: sideloaded APK) | `firetv` |
| Apple tvOS | ❌ not in the App Store (Stremio Lite was listed Oct 2025, pulled Jan 2026); sideload only | none |
| Roku | ❌ no app, none planned | none |
| Hisense VIDAA | ⚠️ only a limited "Stremio Lite" (no streaming-server setting, so stremio++ can't help) | none |
| Fire TV on Vega OS (non-Android, 2025+ sticks) | unknown; no ADB, so `firetv` does not apply | none |

## Per OS

### Samsung Tizen — `samsung` (own client, verified)
- `wss://<tv>:8002/api/v2/channels/samsung.remote.control?name=<base64 name>[&token=…]`, self-signed certificate.
- Pairing: the first connect makes the TV show **Allow/Deny**; `ms.channel.connect` then carries a token, stored as `tv-token`. Later connects send the token, so there's no prompt.
- Keys: `ms.remote.control` / `SendRemoteKey` / `Click` with `KEY_*` names. Text: `SendInputString` (base64) then `SendInputEnd`.
- Own client because `samsungtvws` 3.0.6 (LGPL-3.0) treats the `ms.remote.touchDisable/Enable` events this TV sends before `ms.channel.connect` as failures. The wire format is pinned by `samsung_protocol_test.py` and `samsung_test.py` and must not change.
- There is no play/pause toggle key (Home Assistant sends `KEY_PLAY` or `KEY_PAUSE` depending on state), so the common `PLAY_PAUSE` name is refused on Samsung.

### LG webOS — `webos` (aiowebostv 0.10.0, Apache-2.0)
- SSAP: JSON over WebSocket, `ws://<tv>:3000`. Newer firmware enforces TLS on `wss://<tv>:3001` with a self-signed certificate; aiowebostv tries ws first and falls back to wss.
- Pairing: a `register` message with a signed permission manifest (shipped with the library) makes the TV prompt; accepting returns `client-key`, stored as `tv-webos-client-key`. Later registrations send the key and get no prompt. aiowebostv waits only 10 s for the answer, so the adapter raises that wait to 60 s for `pair`.
- Keys: `ssap://com.webos.service.networkinput/getPointerInputSocket` returns a second socket URL; buttons go there as `type:button\nname:HOME\n\n`.
- Text: `ssap://com.webos.service.ime/insertText {"text", "replace": 0}`, then `sendEnterKey`. This only works while a text field is focused.
- Chosen because it is maintained by home-assistant-libs, async, typed (`py.typed`) and has an Apache licence. It adds aiohttp. `pywebostv` (MIT) is synchronous.

### Android TV / Google TV — `androidtv` (androidtvremote2 0.3.2, Apache-2.0)
- Android TV Remote protocol **v2**, the protocol of the Google TV phone app, served by the preinstalled *Android TV Remote Service*. No developer mode is needed.
- Pairing: TLS to **6467** with a self-signed client certificate. The TV shows a **6-hex-digit code**. The client proves it knows the code by sending SHA-256(client modulus, client exponent, server modulus, server exponent, code[2:]), and the first byte of that hash must equal code[0:2] (androidtvremote2 `pairing.py`). The certificate and key are the credential (`tv-androidtv-cert.pem`/`-key.pem`, mode 600). The adapter deletes them if pairing fails, so `status` means a finished pairing.
- Remote: TLS to **6466** with the same certificate. Protobuf `RemoteMessage`: `remote_key_inject` with Android `KEYCODE_*` values, and an IME batch edit for text.
- **`--code` is not offered.** The TV makes a fresh code each time a pairing connection opens, so the code can't be known before `pair` runs. `pair` prompts for it on stdin instead.
- Chosen because it is maintained (0.3.2, 2026-09), used by Home Assistant's `androidtv_remote` integration, async, typed, and Apache-licensed. It adds `cryptography`, `protobuf` and `aiofiles`.

### Amazon Fire TV (Fire OS) — `firetv` (adb-shell 0.4.4, Apache-2.0)
- Fire OS has **no** Android TV Remote v2 service. The documented LAN route is **ADB over the network**: Settings → My Fire TV → Developer options → **ADB debugging ON**, port **5555** (Amazon lists 5555–5585).
- Pairing: on the first ADB connection from an RSA key, the TV asks *Allow USB debugging?*. The user ticks **Always allow from this computer** and presses OK. The adapter generates its own key (`tv-firetv-adbkey` + `.pub`, mode 600) instead of using `~/.android/adbkey`, so the credential lives with the others.
- Keys: `input keyevent KEYCODE_*`. Names are checked against `^(KEYCODE_[A-Z0-9_]+|[0-9]{1,3})$` before they reach the shell. Text: `input text '<shell-quoted>'` with spaces written as `%s`. `input text` can't type non-ASCII, so the adapter refuses it.
- adb-shell is old (0.4.4, 2023) but stable, used by Home Assistant's `androidtv` integration, async, and Apache-2.0. It is untyped, so the pyright exemptions stay inside `firetv.py`. The alternative was the Homebrew `adb` binary, which keeps its key in `~/.android`. Turning on ADB debugging is a TV-side change and has to be recorded with its revert in the TV runbook.

## Common key vocabulary
`keys.py`: `HOME BACK UP DOWN LEFT RIGHT ENTER PLAY PAUSE PLAY_PAUSE STOP REWIND FAST_FORWARD VOLUME_UP VOLUME_DOWN MUTE MENU INFO`, mapped per OS. Any other name is passed through as a native key. A common name the OS has no key for is an error, not a guess. Android TV and Fire TV share the Android `KEYCODE_*` table.

## Unverified (needs a real TV)
- webOS: the IME text path, the 60 s pairing wait, and wss-only firmware.
- Android TV: pairing UX on Google TV vs older Android TV, and whether `send_text` reaches Stremio's on-screen keyboard (androidtvremote2 warns that IME text "may not work as expected if virtual keyboard is present").
- Fire TV: the auth prompt timing within 60 s, `input text` into Stremio's URL field, and the Developer-options path on current Fire OS 8.
- The revoke steps for webOS and Android TV in the runbook.

## Sources
- Stremio Help Center, Smart TV: https://stremio.zendesk.com/hc/en-us/articles/360021473791-Smart-TV
- Stremio blog, LG 2020+: https://blog.stremio.com/stremio-is-now-available-on-lg-tvs-for-models-2020/
- AFTVnews, Stremio in the Fire TV Appstore: https://www.aftvnews.com/tag/stremio/
- ElfHosted, Stremio on Apple TV (2026): https://docs.elfhosted.com/guides/media/stremio-on-apple-tv/
- VIDAA situation (community port's README): https://github.com/NoobyGains/stremio-vidaa-tv
- Smart-TV install guide (Roku: no app): https://stremio-app.com/install/smart-tv.html
- samsungtvws (key names): https://github.com/xchwarze/samsung-tv-ws-api
- aiowebostv: https://github.com/home-assistant-libs/aiowebostv (`webos_client.py`, `endpoints.py`, `buttons.py`, `handshake.py`)
- PyWebOSTV: https://github.com/supersaiyanmode/PyWebOSTV
- androidtvremote2: https://github.com/tronikos/androidtvremote2 (`pairing.py`, `remotemessage.proto`)
- Android TV Remote v2 protocol write-up: https://github.com/Aymkdn/assistant-freebox-cloud/wiki/Google-TV-(aka-Android-TV)-Remote-Control-(v2)
- Amazon, Connect to Fire TV through ADB: https://developer.amazon.com/docs/fire-tv/connecting-adb-to-device.html
- adb-shell: https://github.com/JeffLIrion/adb_shell
- Android KeyEvent codes: https://developer.android.com/reference/android/view/KeyEvent
