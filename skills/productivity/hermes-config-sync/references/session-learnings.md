# Session Learnings — Multi-Desktop Sync Setup

Learned from a real sync session between two adjacent Windows desktops.

## SSH Key Fingerprint Mismatch

When setting up a new machine, the SSH public key fingerprint will differ from machines you've used before.

**Symptom:**
```
git@github.com: Permission denied (publickey).
```

**Diagnosis:**
```bash
ssh-keygen -lf ~/.ssh/id_ed25519
# Shows: SHA256:<fingerprint> <email>
```

This fingerprint is unique per machine. The one you see in GitHub Settings is just one machine's fingerprint.

**Fix:** Add the new machine's public key to GitHub:
```bash
cat ~/.ssh/id_ed25519.pub
# Copy full output to GitHub → Settings → SSH and GPG keys → New SSH key
```

## Branch Naming: master vs main

First `git push` may create `master` branch instead of `main`.

**Diagnosis:**
```bash
git branch -a
# Shows: * master, remotes/origin/main, remotes/origin/master
```

**Fix:**
```bash
git branch -m master main
git push origin main --force
```

## Hermes Running = state.db Locked

When Hermes desktop app is running, `state.db` and log files are locked by Windows.

**Symptom:**
```
error: unable to unlink old 'state.db': Invalid argument
```

**Workaround — selective checkout:**
```bash
git fetch origin
git checkout origin/main -- config.yaml SOUL.md skills/
```

This pulls only the files you need without touching locked files.

## .env Backup Pattern

Always backup `.env` before any reset operation:

```bash
cp .env .env.backup    # BEFORE
git reset --hard origin/main
cp .env.backup .env    # AFTER
rm .env.backup
```

The `.env.backup` itself should also be gitignored.

## The SQLite Merge Problem

**Problem:** Git cannot merge SQLite database files. Git can only do "last write wins" — so if Desktop A and Desktop B both have different sessions, pushing from one overwrites the other.

**Root cause:** SQLite is a binary format. Git treats it as an opaque blob and cannot diff/merge the contents.

**Solution:** See `references/bidirectional-session-sync.md` for the JSON-based bidirectional sync approach that solves this.

Key insight: Export each session to an individual JSON file. Individual JSON files CAN be merged by Git (text format). Then rebuild the database from merged JSON on each machine.

## Batch Script Path Issues on Windows

When calling Python from batch files, the path detection using `os.path.dirname(__file__)` doesn't work correctly.

**Wrong:**
```python
HERMES_DIR = os.path.dirname(os.path.abspath(__file__))  # Returns script dir, not Hermes dir
```

**Correct:**
```python
HERMES_DIR = os.environ.get('LOCALAPPDATA', '') + '\\hermes'
if not HERMES_DIR or HERMES_DIR == '\\hermes':  # Fallback for edge cases
    HERMES_DIR = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'hermes')
```

## Database Schema Discovery

When Hermes updates, the `state.db` schema may change. Always discover the actual schema from the live database rather than hardcoding:

```python
import sqlite3, os
db = os.environ['LOCALAPPDATA'] + '/hermes/state.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute('PRAGMA table_info(sessions)')
print([r[1] for r in c.fetchall()])
c.execute('PRAGMA table_info(messages)')
print([r[1] for r in c.fetchall()])
```

## Don't Create sqlite_sequence Table

SQLite auto-creates `sqlite_sequence` internally. Manually creating it causes:
```
sqlite3.OperationalError: object name reserved for internal use: sqlite_sequence
```

Omit from CREATE TABLE statements — SQLite handles it automatically.