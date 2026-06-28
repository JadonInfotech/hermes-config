# Windows Hermes Config Path Discovery

## The Problem

Docs and examples say `~/.hermes` but on Windows Hermes Desktop,
this path **does not exist**. The actual location is different.

## Verified Discovery Method

### Step 1: Check the HERMES_HOME environment variable

```bash
echo $HERMES_HOME
# On Windows Hermes Desktop: C:\Users\<user>\AppData\Local\hermes
```

### Step 2: Use Hermes commands (preferred — always correct)

```bash
hermes config path      # prints the actual config.yaml location
hermes config env-path  # prints the .env location
```

### Step 3: Manual inspection (if commands not available)

On Hermes Desktop for Windows, check:
```
C:\Users\<user>\AppData\Local\hermes\
```

## Why the Path is Different

- **Hermes Desktop installer** for Windows stores config in `AppData\Local\hermes`
- **Standalone/portable installs** (via install script on Unix/macOS/WSL) use `~/.hermes`
- The `HERMES_HOME` env var is set by the Hermes Desktop installer to the Windows path

## Converting Between Path Formats

### Windows (in git-bash/MSYS terminal):
| What | Path |
|------|------|
| Config dir | `/c/Users/<user>/AppData/Local/hermes` |
| .env file | `/c/Users/<user>/AppData/Local/hermes/.env` |
| Skills | `/c/Users/<user>/AppData/Local/hermes/skills/` |

### Windows (in PowerShell/CMD):
| What | Path |
|------|------|
| Config dir | `C:\Users\<user>\AppData\Local\hermes` |
| .env file | `C:\Users\<user>\AppData\Local\hermes\.env` |
| Skills | `C:\Users\<user>\AppData\Local\hermes\skills\` |

### Unix/macOS/WSL:
| What | Path |
|------|------|
| Config dir | `~/.hermes` |
| .env file | `~/.hermes/.env` |
| Skills | `~/.hermes/skills/` |

## SSH Key Location

SSH keys are stored at `~/.ssh/` which on Windows git-bash resolves to:
```
C:\Users\<user>\.ssh\
```

This path is consistent across Windows — SSH config always lives here,
independent of where Hermes is installed.

## Session Storage Location

**Sessions are stored in `state.db`, NOT in `sessions/` directory.**
- The `sessions/` folder is empty (just a routing index)
- All conversation history, messages, and FTS indexes are in `state.db`
- This means syncing `state.db` syncs all session history

## File Locking Issues

When Hermes is running on Windows, these files are LOCKED:
- `state.db` (always locked while Hermes running)
- `state.db-shm` (SQLite shared memory)
- `state.db-wal` (SQLite WAL journal)
- `logs/*.lock` files

**Workaround:** Use `git checkout origin/main -- <files>` instead of `git reset --hard` for file-by-file sync when files are locked.

## Git LFS Requirement

`state.db` (typically 1-2MB) may exceed GitHub's 50MB soft limit without Git LFS:
```bash
git lfs install
git lfs track "*.db"
git add .gitattributes
```

## SSH Setup on Windows

### Start SSH Agent and Add Key
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

### Add GitHub Host Keys
```bash
ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> ~/.ssh/known_hosts 2>/dev/null
```

### Verify Connection
```bash
ssh -T git@github.com
# Expected: "Hi <username>! You've successfully authenticated..."
```