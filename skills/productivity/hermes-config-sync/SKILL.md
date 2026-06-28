---
name: hermes-config-sync
description: "Sync Hermes Agent config across multiple machines via GitHub."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
tags: [hermes, git, sync, multi-machine, setup]
---

# Hermes Config Sync

Sync your Hermes config directory (`~/.hermes` or `$HERMES_HOME`) across multiple machines using a GitHub repo.

Supports two sync modes:
- **Config-only** (default): sync `config.yaml`, `SOUL.md`, and skills — sessions stay local
- **Full sync**: also sync `state.db` (session history) and `memories/` — for multi-machine workflows where you want access to all conversations from any desktop

## Quick Start

### First Machine: Push Config

```bash
cd ~/.hermes
git init
git remote add origin git@github.com:<org>/hermes-config.git

# Create .gitignore (critical: excludes .env and other sensitive files)
cat > .gitignore << 'EOF'
# Secrets - NEVER commit
.env
.env.*
auth.json
auth.json.*
auth.lock

# Hermes bundled binaries
bin/
shared/
git/
node/
node_modules/
cache/
bootstrap-cache/

# Cron lock files
cron/.jobs.lock
cron/.tick.lock
cron/ticker_*
cron/heartbeat
cron/last_success

# State snapshots
state-snapshots/

# OS files
.DS_Store
Thumbs.db

# Hermes installer
desktop-build-stamp.json
hermes-setup.exe

# Misc Hermes files (user-specific, regenerate on new machine)
.skills_prompt_snapshot.json
.update_check
.update_exit_code
ollama_cloud_models_cache.json
models_dev_cache.json

# --- CHOOSE ONE SECTION BELOW ---

# OPTION A: Config-only sync (default — sessions stay local)
logs/
pairing/
hooks/

# OPTION B: Full sync (sync sessions + memories across machines)
# Uncomment these lines if you want session history on every machine:
# state.db
# state.db-shm
# state.db-wal
# memories/
EOF

git add .
git commit -m "Initial config"
git push origin main
```

> **Branch name tip:** Use `main` as your default branch. First push may accidentally go to `master` — rename with `git branch -m master main && git push origin main --force`.

### Additional Machines: Pull Config

**Step 1: SSH Key Setup (one-time)**

```bash
# Add GitHub to known hosts
ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> ~/.ssh/known_hosts

# Start SSH agent and add key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Verify connection
ssh -T git@github.com
# Should see: "Hi <username>! You've successfully authenticated..."
```

If you get `Permission denied (publickey)`:
```bash
# Show your public key
cat ~/.ssh/id_ed25519.pub

# Copy output → GitHub → Settings → SSH and GPG keys → New SSH key
```

**Step 2: Sync Config**

Two approaches depending on whether Hermes desktop app is running:

**Option A: Hermes is running (state.db locked)**
```bash
cd ~/.hermes

# Backup .env (API keys — never lose this)
cp .env .env.backup

# Use git checkout to pull specific files/dirs (avoids state.db lock)
git fetch origin
git checkout origin/main -- config.yaml SOUL.md skills/

# Restore your .env
cp .env.backup .env
rm .env.backup
```

**Option B: Hermes is closed (full reset)**
```bash
cd ~/.hermes

# Backup .env
cp .env .env.backup

# Full reset — works when no files are locked
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
| `unable to unlink old 'state.db'` | Use Option A (git checkout) above, or close Hermes |
| `untracked working tree files would be overwritten` | Use `git reset --hard origin/main` |
| `refusing to merge unrelated histories` | Use `git pull --allow-unrelated-histories` |
| First push went to `master` instead of `main` | `git branch -m master main && git push origin main --force` |

## What Gets Synced

**Always synced:**
- Config: `config.yaml`, `SOUL.md`
- Skills: entire `skills/` directory

**Optionally synced (enable in .gitignore):**
- `state.db` — session history, conversation metadata
- `memories/` — persistent memory files

**Never synced (always local):**
- `.env` — API keys and secrets
- `auth.json` — OAuth tokens
- `logs/` — runtime logs
- `cache/` — model caches
- `bin/`, `shared/` — Hermes binaries

---

**Session learnings:** See `references/session-learnings.md` for real-world patterns from multi-desktop sync setups (SSH fingerprint mismatches, branch naming gotchas, state.db locking workarounds).