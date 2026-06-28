# Bidirectional Session Sync — True Two-Way Merging

The Problem: SQLite (`state.db`) cannot be merged by Git. Git can only do "last write wins" — so if Desktop A and Desktop B both have different sessions, pushing from one overwrites the other.

Solution: Export sessions to individual JSON files (which Git CAN merge), sync those via Git, then rebuild the database on each machine.

## How It Works

```
Desktop A                           GitHub                          Desktop B
    │                                  │                                 │
    ├─ Export state.db → JSON ────────►│                                 │
    │                                  │◄─────────── Export ─────────────┤
    │                                  │                                 │
    │◄──── Pull & Merge JSONs ─────────┤                                 │
    │                                  │─────── Pull & Merge JSONs ──────►│
    │                                  │                                 │
    ├─ Rebuild state.db ← JSON ────────│◄─────────── Rebuild ────────────┤
    │                                  │                                 │
```

## Directory Structure

```
~/.hermes/
├── sync_sessions/              # Individual session JSON files (synced)
│   ├── 20260615_224206_01466a.json
│   └── 20260628_093422_session2.json
├── scripts/
│   ├── export_sessions.py      # state.db → JSON files
│   └── import_sessions.py      # JSON files → state.db
├── state.db                    # Local only (rebuilt from sync_sessions/)
└── sync-bidirectional.bat       # Main sync script
```

## .gitignore for Bidirectional Sync

```gitignore
# Secrets - NEVER commit
.env
.env.*
auth.json
auth.json.*
auth.lock

# Hermes bundled binaries
bin/
shared/
cache/
bootstrap-cache/

# Session database - use sync_sessions JSON files instead
state.db
state.db-*
state_new.db

# Other local-only files
logs/
memories/
pairing/
hooks/
cron/.jobs.lock
cron/.tick.lock
cron/ticker_*
cron/heartbeat
cron/last_success
state-snapshots/
```

## Database Schema (Hermes state.db)

Get the actual schema by querying the live database:

```python
import sqlite3, os
db = os.environ['LOCALAPPDATA'] + '/hermes/state.db'
conn = sqlite3.connect(db)
c = conn.cursor()

# Sessions table (35 columns)
c.execute('PRAGMA table_info(sessions)')
print('Sessions:', [r[1] for r in c.fetchall()])

# Messages table (19 columns)
c.execute('PRAGMA table_info(messages)')
print('Messages:', [r[1] for r in c.fetchall()])
```

**Sessions columns:**
```
id, source, user_id, model, model_config, system_prompt, parent_session_id,
started_at, ended_at, end_reason, message_count, tool_call_count, input_tokens,
output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens, cwd,
billing_provider, billing_base_url, billing_mode, estimated_cost_usd, actual_cost_usd,
cost_status, cost_source, pricing_version, title, api_call_count, handoff_state,
handoff_platform, handoff_error, rewind_count, archived, git_branch, git_repo_root
```

**Messages columns:**
```
id (autoincrement), session_id, role, content, tool_call_id, tool_calls, tool_name,
timestamp, token_count, finish_reason, reasoning, reasoning_content, reasoning_details,
codex_reasoning_items, codex_message_items, platform_message_id, observed, active, compacted
```

## Workflow Per Desktop

### First Time Setup (each desktop, run once)

1. Close Hermes desktop app
2. Run `sync-bidirectional.bat`
3. Done — sessions sync automatically after this

### Ongoing Sync (before each Hermes session)

1. Close Hermes
2. Run `sync-bidirectional.bat`
3. Start Hermes

## Key Scripts

### export_sessions.py

```python
#!/usr/bin/env python3
"""Export Hermes sessions from state.db to individual JSON files."""

import sqlite3
import json
import os
from datetime import datetime

HERMES_DIR = os.environ.get('LOCALAPPDATA', '') + '\\hermes'
DB_PATH = os.path.join(HERMES_DIR, 'state.db')
EXPORT_DIR = os.path.join(HERMES_DIR, 'sync_sessions')

def export_sessions():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    
    if not os.path.exists(DB_PATH):
        print('No state.db found')
        return True
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM sessions')
    sessions_cols = [desc[0] for desc in cursor.description]
    
    rows = cursor.fetchall()
    print(f'Found {len(rows)} sessions to export')
    
    for row in rows:
        session = dict(zip(sessions_cols, row))
        session_id = session['id']
        
        cursor.execute('SELECT * FROM messages WHERE session_id = ?', (session_id,))
        msg_cols = [desc[0] for desc in cursor.description]
        messages = [dict(zip(msg_cols, msg_row)) for msg_row in cursor.fetchall()]
        
        session['messages'] = messages
        session['exported_at'] = datetime.now().isoformat()
        session['exported_from'] = os.environ.get('COMPUTERNAME', 'unknown')
        
        safe_id = session_id.replace(':', '_').replace('-', '_').replace('.', '_')
        filepath = os.path.join(EXPORT_DIR, f'{safe_id}.json')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
        
        print(f"  Exported: {session_id} ({len(messages)} messages)")
    
    conn.close()
    return True

if __name__ == '__main__':
    export_sessions()
```

### import_sessions.py

```python
#!/usr/bin/env python3
"""Import Hermes sessions from JSON files back into state.db."""

import sqlite3
import json
import os
import glob
import subprocess

HERMES_DIR = os.environ.get('LOCALAPPDATA', '') + '\\hermes'
DB_PATH = os.path.join(HERMES_DIR, 'state.db')
EXPORT_DIR = os.path.join(HERMES_DIR, 'sync_sessions')

def import_sessions():
    session_files = glob.glob(os.path.join(EXPORT_DIR, '*.json'))
    print(f'Found {len(session_files)} session files to import')
    
    if not session_files:
        print('No sessions to import')
        return True
    
    # Check if Hermes is running
    result = subprocess.run(['tasklist'], capture_output=True, text=True)
    if 'Hermes.exe' in result.stdout:
        print('WARNING: Hermes is running! Close Hermes first for full import.')
        return True
    
    # Backup and create new database
    backup_path = DB_PATH + '.backup'
    if os.path.exists(DB_PATH):
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(DB_PATH, backup_path)
        except PermissionError:
            print('Cannot backup database - file locked')
            return True
    
    new_db = DB_PATH + '.new'
    if os.path.exists(new_db):
        os.remove(new_db)
    
    conn = sqlite3.connect(new_db)
    
    # Create tables with EXACT schema
    conn.execute('''
    CREATE TABLE sessions (
        id TEXT PRIMARY KEY, source TEXT, user_id TEXT, model TEXT, model_config TEXT,
        system_prompt TEXT, parent_session_id TEXT, started_at REAL, ended_at REAL,
        end_reason TEXT, message_count INTEGER, tool_call_count INTEGER, input_tokens INTEGER,
        output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER,
        reasoning_tokens INTEGER, cwd TEXT, billing_provider TEXT, billing_base_url TEXT,
        billing_mode TEXT, estimated_cost_usd REAL, actual_cost_usd REAL, cost_status TEXT,
        cost_source TEXT, pricing_version TEXT, title TEXT, api_call_count INTEGER,
        handoff_state TEXT, handoff_platform TEXT, handoff_error TEXT, rewind_count INTEGER,
        archived INTEGER, git_branch TEXT, git_repo_root TEXT
    )
    ''')
    
    conn.execute('''
    CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT,
        tool_call_id TEXT, tool_calls TEXT, tool_name TEXT, timestamp REAL, token_count INTEGER,
        finish_reason TEXT, reasoning TEXT, reasoning_content TEXT, reasoning_details TEXT,
        codex_reasoning_items TEXT, codex_message_items TEXT, platform_message_id TEXT,
        observed INTEGER, active INTEGER, compacted INTEGER
    )
    ''')
    
    conn.execute('''
    CREATE VIRTUAL TABLE messages_fts 
    USING fts5(session_id, role, content, content="messages", content_rowid="id")
    ''')
    
    conn.execute('CREATE TABLE schema_version (version INTEGER)')
    conn.execute('CREATE TABLE state_meta (key TEXT PRIMARY KEY, value TEXT, updated_at REAL)')
    conn.execute('CREATE TABLE compression_locks (session_id TEXT PRIMARY KEY)')
    conn.execute('INSERT INTO schema_version VALUES (1)')
    
    # Import sessions
    for filepath in session_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            session = json.load(f)
        
        session_id = session.get('id', '')
        session_cols = ['id', 'source', 'user_id', 'model', 'model_config', 'system_prompt',
            'parent_session_id', 'started_at', 'ended_at', 'end_reason', 'message_count',
            'tool_call_count', 'input_tokens', 'output_tokens', 'cache_read_tokens',
            'cache_write_tokens', 'reasoning_tokens', 'cwd', 'billing_provider',
            'billing_base_url', 'billing_mode', 'estimated_cost_usd', 'actual_cost_usd',
            'cost_status', 'cost_source', 'pricing_version', 'title', 'api_call_count',
            'handoff_state', 'handoff_platform', 'handoff_error', 'rewind_count',
            'archived', 'git_branch', 'git_repo_root']
        
        session_data = [session.get(col) for col in session_cols]
        conn.execute(f'INSERT OR REPLACE INTO sessions VALUES ({",".join(["?"]*35)})', session_data)
        
        # Import messages
        for msg in session.get('messages', []):
            msg['session_id'] = session_id
            msg_cols = ['session_id', 'role', 'content', 'tool_call_id', 'tool_calls', 'tool_name',
                       'timestamp', 'token_count', 'finish_reason', 'reasoning', 'reasoning_content',
                       'reasoning_details', 'codex_reasoning_items', 'codex_message_items',
                       'platform_message_id', 'observed', 'active', 'compacted']
            msg_data = [msg.get(col) for col in msg_cols]
            conn.execute(f'INSERT INTO messages VALUES ({",".join(["?"]*18)})', msg_data)
        
        print(f"  Imported: {session_id}")
    
    conn.commit()
    conn.close()
    os.rename(new_db, DB_PATH)
    print('Database rebuilt successfully!')
    return True

if __name__ == '__main__':
    import_sessions()
```

### sync-bidirectional.bat

```batch
@echo off
echo ========================================
echo   Hermes Bidirectional Sync
echo ========================================

cd /d "%LOCALAPPDATA%\hermes"

echo [1] Checking if Hermes is running...
tasklist | findstr /I "Hermes.exe" >nul
if %errorlevel%==0 (
    echo  WARNING: Hermes running - import will be skipped
)

echo [2] Exporting sessions...
python "%LOCALAPPDATA%\hermes\scripts\export_sessions.py"

echo [3] Git: Fetch/Commit/Push...
git fetch origin main
git add sync_sessions/ memories/ config.yaml SOUL.md skills/ scripts/
git commit -m "Sync from %computername% %date% %time%" 2>nul
git pull origin main --no-edit 2>nul
git push origin main

echo [4] Importing sessions...
python "%LOCALAPPDATA%\hermes\scripts\import_sessions.py"

echo ========================================
echo   SYNC COMPLETE!
echo ========================================
pause
```

## Common Issues

### Python not found
Ensure Python is installed and in PATH. Test with:
```bash
python --version
```

### Database locked (Hermes still running)
The script detects this and:
- Export still works (read-only)
- Import is skipped with warning
- Run script again after closing Hermes

### Empty sync_sessions folder
Check that export script ran successfully. Verify:
```bash
ls sync_sessions/
```

### Import fails with column count mismatch
Schema has changed in a Hermes update. Re-run:
```python
# Check current schema
c.execute('PRAGMA table_info(sessions)')
c.execute('PRAGMA table_info(messages)')
```

Then update the CREATE TABLE statements in import_sessions.py.

## Git LFS (Optional)

For very large session files, enable Git LFS:
```bash
git lfs install
git lfs track "*.json"
echo "*.json filter=lfs diff=lfs merge=lfs -text" >> .gitattributes
```
