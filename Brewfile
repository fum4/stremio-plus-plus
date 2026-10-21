# System deps for the Mac host. `mise run setup` applies this.
# Language toolchains (python, uv, node) are pinned in .mise.toml instead.
brew "mise"
brew "ffmpeg"   # ffprobe/ffmpeg: audio extraction; also the streaming server's transcoder
brew "age"      # repo secrets (devbox repo-secrets engine)
brew "bash"     # repo-secrets needs bash >= 4 (mapfile); macOS ships 3.2
brew "gh"
brew "lego"   # Let's Encrypt client: the addon's certificate via DNS-01 (mise run tls:renew)
brew "alass"    # subtitle sync fallback (splits/ad breaks ffsubsync can't handle); no macOS release binary upstream
