# March 1, 2026 — Session Summary

## Spotify Link Resolution + AssemblyAI Transcription

Implemented the full pipeline for sending Spotify episode links to the podcast bot and getting summaries back.

### Files changed
- **`app/config.py`** — Replaced `deepgram_api_key` with `assemblyai_api_key`, `podcastindex_api_key`, `podcastindex_api_secret`
- **`.env.example`** — Updated placeholders to match new keys
- **`app/common/audio.py`** — Replaced stub with real AssemblyAI integration (submit + poll, 5s interval, 30min timeout)
- **`app/bots/podcast/spotify.py`** — New file: resolves Spotify episode URLs to direct MP3 URLs via Spotify oEmbed + PodcastIndex API + fuzzy title matching
- **`app/bots/podcast/router.py`** — Added Spotify URL detection, `_process_spotify_episode()` wrapper with status messages and error handling

### Bugs fixed during testing
- oEmbed title doesn't always use "Episode - Show" format — added fallback to scrape show name from Spotify page meta tags
- PodcastIndex feed search was blindly picking the first result — added fuzzy matching on feed title
- AssemblyAI now requires `speech_models: ["universal-3-pro"]` in the request body
- Removed stale `DEEPGRAM_API_KEY` from `.env` that was causing pydantic validation error

---

## AWS Deployment

Deployed the app to AWS so it runs without a local server or ngrok.

### Infrastructure set up
- **RDS** — PostgreSQL `db.t4g.micro`, Single-AZ, 20GB storage, private access (no public IP)
- **EC2** — `t3.micro`, Amazon Linux 2023, 8GB storage
- **Security groups** — EC2 allows SSH (22), HTTPS (443), custom TCP (8000); RDS allows PostgreSQL (5432) from EC2's security group only
- **DuckDNS** — Free subdomain `norty-agents.duckdns.org` pointing to EC2 public IP
- **Caddy** — Reverse proxy on EC2 handling automatic HTTPS via Let's Encrypt

### Deployment pipeline
- **`.github/workflows/deploy.yml`** — GitHub Action that on push to `main`: SSHs into EC2, pulls latest code, syncs deps, restarts the systemd service
- **GitHub Secrets** — `EC2_SSH_KEY` (PEM file) and `EC2_HOST` (EC2 public IP)
- **systemd service** — `personal-agents.service` on EC2 auto-starts the app on boot and restarts on crash

### Key details
- EC2 public IP: `3.147.44.235`
- RDS endpoint: `personal-agents.ctq8wc62m8wh.us-east-2.rds.amazonaws.com`
- Webhook URL: `https://norty-agents.duckdns.org`
- DBeaver connects via SSH tunnel through EC2 to reach RDS
