@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   Hermes True Bidirectional Sync
echo   Run this BEFORE starting Hermes
echo ========================================
echo.

cd /d "%LOCALAPPDATA%\hermes"
set "SESSION_DIR=%LOCALAPPDATA%\hermes\sync_sessions"

echo [1/10] Ensuring Hermes is not running...
tasklist | findstr /I "Hermes.exe" >nul
if %errorlevel%==0 (
    echo    ERROR: Hermes is still running!
    echo    Please close Hermes first, then run this script again.
    pause
    exit /b 1
)

echo.
echo [2/10] Creating session sync directory...
if not exist "sync_sessions" mkdir sync_sessions

echo.
echo [3/10] Exporting local sessions to individual JSON files...
python -c "
import sqlite3
import json
import os
from datetime import datetime

conn = sqlite3.connect('state.db')
cursor = conn.cursor()

# Get all sessions with their messages
cursor.execute('SELECT * FROM sessions')
sessions_cols = [desc[0] for desc in cursor.description]

cursor.execute('SELECT * FROM messages')
messages_cols = [desc[0] for desc in cursor.description]
if messages_cols[0] == 'id':
    messages_cols = messages_cols[1:]  # Remove auto-increment id

os.makedirs('sync_sessions', exist_ok=True)

session_count = 0
for row in cursor.execute('SELECT * FROM sessions'):
    session = dict(zip(sessions_cols, row))
    session_id = session['id']
    
    # Get messages for this session
    cursor.execute('SELECT * FROM messages WHERE session_id = ?', (session_id,))
    messages = []
    for msg_row in cursor.fetchall():
        # Skip the auto-increment id if present
        if messages_cols:
            msg = dict(zip(['session_id'] + messages_cols, msg_row))
        else:
            msg = {}
        messages.append(msg)
    
    session['messages'] = messages
    session['exported_at'] = datetime.now().isoformat()
    session['exported_from'] = '%computername%'
    
    # Write each session to its own file
    safe_id = session_id.replace(':', '_').replace('-', '_')
    filepath = f'sync_sessions/{safe_id}.json'
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(session, f, ensure_ascii=False, indent=2)
    session_count += 1

conn.close()
print(f'Exported {session_count} sessions to sync_sessions/')
" 2>nul

if %errorlevel% neq 0 (
    echo    ERROR: Failed to export sessions.
    echo    Make sure Python is installed and try again.
    pause
    exit /b 1
)

echo.
echo [4/10] Fetching latest changes from GitHub...
git fetch origin main

echo.
echo [5/10] Committing local session files...
git add sync_sessions/
git add memories/
git add config.yaml
git add SOUL.md
git add skills/
git add .gitignore
git add sync-bidirectional.bat
git add .gitattributes
git commit -m "Sessions from %computername% - %date% %time%" 2>nul
if %errorlevel% neq 0 (
    echo    No changes to commit.
)

echo.
echo [6/10] Pulling and merging from GitHub...
git pull origin main --no-edit 2>&1

echo.
echo [7/10] Pushing to GitHub...
git push origin main

echo.
echo [8/10] Checking for merged sessions...
python -c "
import os
import json
import glob

session_files = glob.glob('sync_sessions/*.json')
print(f'Found {len(session_files)} session files')
for f in sorted(session_files):
    print(f'  {os.path.basename(f)}')
" 2>nul

echo.
echo [9/10] Rebuilding local database from synced sessions...
python -c "
import sqlite3
import json
import os
import glob
from datetime import datetime

# Get all session JSON files
session_files = glob.glob('sync_sessions/*.json')
print(f'Importing {len(session_files)} sessions...')

# Create new database
conn = sqlite3.connect('state_new.db')

# Create sessions table
conn.execute('''
CREATE TABLE IF NOT EXISTS sessions (
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

# Create messages table (without auto-increment id)
conn.execute('''
CREATE TABLE IF NOT EXISTS messages (
    session_id TEXT, role TEXT, content TEXT,
    tool_calls TEXT, tool_result TEXT, model TEXT, provider TEXT, input_tokens INTEGER,
    output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER,
    reasoning_tokens INTEGER, created_at REAL, completed_at REAL, error TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
)
''')

# Create FTS table for full-text search
conn.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts 
    USING fts5(session_id, role, content, content="messages", content_rowid="rowid")''')

# Create state_meta table
conn.execute('''
CREATE TABLE IF NOT EXISTS state_meta (key TEXT PRIMARY KEY, value TEXT, updated_at REAL)
''')

conn.execute('CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)')
conn.execute('CREATE TABLE IF NOT EXISTS sqlite_sequence (name, seq)')

# Import each session
sessions_imported = 0
messages_imported = 0
for filepath in session_files:
    with open(filepath, 'r', encoding='utf-8') as f:
        session = json.load(f)
    
    # Extract session data (exclude 'messages' and metadata)
    session_keys = ['id', 'source', 'user_id', 'model', 'model_config', 'system_prompt',
        'parent_session_id', 'started_at', 'ended_at', 'end_reason', 'message_count',
        'tool_call_count', 'input_tokens', 'output_tokens', 'cache_read_tokens',
        'cache_write_tokens', 'reasoning_tokens', 'cwd', 'billing_provider',
        'billing_base_url', 'billing_mode', 'estimated_cost_usd', 'actual_cost_usd',
        'cost_status', 'cost_source', 'pricing_version', 'title', 'api_call_count',
        'handoff_state', 'handoff_platform', 'handoff_error', 'rewind_count',
        'archived', 'git_branch', 'git_repo_root']
    
    session_data = {k: session.get(k) for k in session_keys}
    
    # Convert None to appropriate defaults
    for key in session_data:
        if session_data[key] is None:
            if key in ['message_count', 'tool_call_count', 'input_tokens', 'output_tokens',
                       'cache_read_tokens', 'cache_write_tokens', 'reasoning_tokens',
                       'api_call_count', 'rewind_count', 'archived']:
                session_data[key] = 0
            elif key in ['started_at', 'ended_at', 'updated_at', 'created_at', 'completed_at']:
                session_data[key] = 0.0
            elif key in ['estimated_cost_usd', 'actual_cost_usd']:
                session_data[key] = 0.0
    
    placeholders = ','.join(['?' for _ in session_keys])
    try:
        conn.execute(f'INSERT OR REPLACE INTO sessions VALUES ({placeholders})',
                    [session_data[k] for k in session_keys])
        sessions_imported += 1
    except Exception as e:
        print(f'Error importing session: {e}')
    
    # Import messages
    for msg in session.get('messages', []):
        msg_keys = ['session_id', 'role', 'content', 'tool_calls', 'tool_result',
                   'model', 'provider', 'input_tokens', 'output_tokens', 'cache_read_tokens',
                   'cache_write_tokens', 'reasoning_tokens', 'created_at', 'completed_at', 'error']
        msg_data = {k: msg.get(k) for k in msg_keys}
        try:
            placeholders = ','.join(['?' for _ in msg_keys])
            conn.execute(f'INSERT INTO messages VALUES ({placeholders})',
                        [msg_data[k] for k in msg_keys])
            messages_imported += 1
        except Exception as e:
            pass

conn.execute('INSERT INTO schema_version VALUES (1)')

conn.commit()
conn.close()

print(f'Imported {sessions_imported} sessions, {messages_imported} messages')

# Replace old database
if os.path.exists('state.db.bak'):
    os.remove('state.db.bak')
if os.path.exists('state.db'):
    os.rename('state.db', 'state.db.bak')
os.rename('state_new.db', 'state.db')
if os.path.exists('state.db.bak'):
    os.remove('state.db.bak')

print('Database rebuilt successfully!')
"

echo.
echo [10/10] Cleanup...
if exist "sync_sessions" (
    echo    Session files kept for next sync.
)

echo.
echo ========================================
echo   Bidirectional Sync Complete!
echo   All sessions synced with GitHub.
echo ========================================
echo.
pause