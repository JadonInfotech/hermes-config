---
name: hermes-config-sync
description: "Sync Hermes Agent config across multiple machines via GitHub."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
tags: [hermes, git, sync, multi-machine, setup]
---

# Hermes Config Sync

Sync your Hermes config directory (`~/.hermes` or `$HERMES_HOME`) across multiple machines using a GitHub repo.

## Quick Start

### First Machine: Push Config

```bash
cd ~/.hermes
git init
git remote add origin git@github.com:<org>/hermes-config.git

# Create .gitignore (critical: excludes .env and other sensitive files)
cat > .gitignore << 'EOF'
.env
.env.*
auth.json
auth.lock
logs/
sessions/
memories/
cron/
cache/
bootstrap-cache/
image_cache/
audio_cache/
shared/
bin/
hermes-setup.exe
desktop-build-stamp.json
models_dev_cache.json
ollama_cloud_models_cache.json
*.db
*.db-*
state-snapshots/
hooks/
pairing/
EOF

git add .
git commit -m "Initial config"
git push origin main
```

### Additional Machines: Pull Config

**Step 1: SSH Key Setup (one-time)**

```bash
# Add GitHub to known hosts
ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> ~/.ssh/known_hosts

# Add SSH key to agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

If you get `Permission denied (publickey)`, add your public key to GitHub:
```bash
cat ~/.ssh/id_ed25519.pub
# Copy output → GitHub → Settings → SSH and GPG keys → New SSH key
```

**Step 2: Sync Config**

> ⚠️ **Close Hermes desktop app first** — running instances lock `state.db` and log files, causing `git reset --hard` to fail with `unable to unlink old 'state.db': Invalid argument`.

```bash
cd ~/.hermes

# Backup .env (API keys — never commit this)
cp .env .env.backup

# Pull from repo
git fetch origin
git reset --hard origin/main

# Restore your .env
cp .env.backup .env
rm .env.backup
```

**Step 3: Verify**

```bash
hermes doctor
```

## Pushing Updates

After changing config or skills on any machine:

```bash
cd ~/.hermes
git add .
git commit -m "Update config"
git push origin main
```

Other machines: run `git pull origin main` (or `git fetch && git reset --hard origin/main`) to sync.

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Host key verification failed` | Run `ssh-keyscan` above |
| `Permission denied (publickey)` | Add public key to GitHub Settings |
| `unable to unlink old 'state.db'` | Close Hermes desktop app completely |
| `untracked working tree files would be overwritten` | Use `git reset --hard origin/main` |
| `refusing to merge unrelated histories` | Use `git pull --allow-unrelated-histories` |

## What Gets Synced

✅ Config files: `config.yaml`, `SOUL.md`
✅ Skills: entire `skills/` directory
✅ Project context files from nested directories

❌ Never synced: `.env` (API keys), session history, auth tokens, logs, caches