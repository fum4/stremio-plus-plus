# Owner actions

## 2026-10-21
- [ ] 🔴 **Before deploying the first-run setup PR on Batman** — add to `.env.local`: `ADDON_DOMAIN=stremio.nomadware.io`, `TV_HOST=192.168.1.134`, `TV_OS=samsung` (they leave the committed `companion.env`). Or, to run the zero-config path on purpose (new stremio.rocks addon URL and token: reinstall the addon), add `ADDON_DOMAIN=` (empty). With neither, the companion refuses to start (age key present) rather than switch the addon URL silently. Then `mise run host:doctor` must show the own-domain checks.
- [ ] 🔴 **Renew `nomadware.io`** — expires **2026-10-30** (GoDaddy → My Products → nomadware.io → Renew / Auto-renew on). The permanent HTTPS address for the addon builds on it. Reply: "renewed".
- [ ] 🟡 **DHCP reservation for Batman** — router `http://192.168.1.1` → Address Reservation → MAC `22:3c:5b:52:a1:8f` → `192.168.1.132` ([runbook §1](docs/runbooks/tv-setup.md#1-give-the-mac-a-fixed-lan-ip)). The TV's server URL contains this IP.
- [ ] 🟡 **DHCP reservation for the TV** — router → Address Reservation → MAC `d0:c2:4e:13:e0:49` → `192.168.1.134` (the host controls the TV at that address).
- [ ] 🟡 **DNS for `nomadware.io`** — move to Cloudflare (recommended: free, API for certificates) or keep GoDaddy. Reply: "move to Cloudflare" / "keep GoDaddy".
- [ ] 🟡 **Merge PRs #1 → #7** on GitHub (stacked, each gated green), or tell the agent to merge them.
- [ ] ⚪ **Revert check** — once: TV server URL → `http://127.0.0.1:11470`, play something, switch back ([runbook §4](docs/runbooks/tv-setup.md#4-revert)). Confirms the one-setting revert.
- [ ] ⚪ **repo-secrets on macOS** — engine installed with the `$TMPDIR` fallback (option a). Escrow of the repo age key into devbox still to do (agent task once devbox access is decided).
- [ ] ⚪ **Where Batman's machine config lives** — see `docs/work/tbd.md`.
