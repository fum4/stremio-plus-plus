# `secrets/` — stremio-companion's encrypted secrets

age-encrypted and committed next to the code; decrypted with the stremio-companion age key
(`~/.config/age/stremio-companion.key`). Pattern and commands: devbox `docs/repo-secrets.md`.

| File | Holds | Read by |
|---|---|---|
| `recipients.txt` | the owners' age public keys | `repo-secrets` (encrypt target) |
| `acme.env.age` | `CF_DNS_API_TOKEN`: Cloudflare account token `stremio-companion-acme` (DNS·Write on `nomadware.io` only) for Let's Encrypt DNS-01 | `mise run tls:renew` via `repo-secrets exec` |
| `companion.env.age` | `ADDON_TOKEN`: the secret path segment of the addon URL (`https://stremio.nomadware.io:8443/<token>/manifest.json`) | the companion, via `repo-secrets exec` in its launchd agent |

macOS notes: the engine needs bash ≥ 4 (Brewfile `bash`) and is installed by `mise run tools:repo-secrets` (pinned devbox commit, sha256-checked). `secrets:edit` uses `$TMPDIR` (per-user, 0700, **disk-backed**) because macOS has no tmpfs.
