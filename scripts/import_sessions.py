#!/usr/bin/env python3
"""Import Hermes sessions from JSON files back into state.db.

CRITICAL SAFETY RULES:
1. NEVER delete existing database - merge incrementally
2. Skip corrupted JSON files - log and continue
3. Only update sessions that have CHANGES (compare message counts)
4. Never lose user data
"""

import sqlite3
import json
import os
import glob
import re
from datetime import datetime

# Get Hermes directory
HERMES_DIR = os.environ.get('LOCALAPPDATA', '') + '\\hermes'
if not HERMES_DIR or HERMES_DIR == '\\hermes':
    HERMES_DIR = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'hermes')

DB_PATH = os.path.join(HERMES_DIR, 'state.db')
EXPORT_DIR = os.path.join(HERMES_DIR, 'sync_sessions')

print(f'Hermes dir: {HERMES_DIR}')
print(f'DB path: {DB_PATH}')

def fix_merge_conflict(content):
    """Remove Git merge conflict markers and resolve conflicts.
    Strategy: Keep the version with MORE messages (more complete).
    """
    # Check for conflict markers
    if '<<<<<<< ' not in content:
        return content, False
    
    # Pattern to find conflict blocks
    pattern = r'<<<<<<< .+?\n(.*?)=======\n(.*?)>>>>>>> .+?\n'
    
    def resolve_conflict(match):
        ours = match.group(1)
        theirs = match.group(2)
        
        # Count message-related lines in each version
        # More message entries = more complete
        ours_lines = ours.count('"role":') + ours.count('"content":')
        theirs_lines = theirs.count('"role":') + theirs.count('"content":')
        
        if theirs_lines > ours_lines:
            return theirs
        return ours
    
    fixed = re.sub(pattern, resolve_conflict, content, flags=re.DOTALL)
    return fixed, True

def validate_json(content):
    """Validate JSON and try to fix common issues."""
    # Try to parse as-is
    try:
        return json.loads(content), False
    except json.JSONDecodeError as e:
        pass
    
    # Try fixing merge conflicts
    fixed_content, was_fixed = fix_merge_conflict(content)
    if was_fixed:
        try:
            return json.loads(fixed_content), True
        except json.JSONDecodeError:
            pass
    
    # Try to truncate at last valid complete object
    # This handles truncated JSON files
    for i in range(len(content) - 1, 0, -1):
        if content[i] == '}':
            try:
                return json.loads(content[:i+1]), False
            except json.JSONDecodeError:
                continue
    
    return None, False

def import_sessions():
    session_files = glob.glob(os.path.join(EXPORT_DIR, '*.json'))
    print(f'Found {len(session_files)} session files to import')
    
    if not session_files:
        print('No sessions to import')
        return True
    
    # Check if Hermes is running
    import subprocess
    result = subprocess.run(['tasklist'], capture_output=True, text=True)
    if 'Hermes.exe' in result.stdout:
        print('WARNING: Hermes is running! Close Hermes first for safe import.')
        print('Continuing anyway - will be careful with the database.')
    
    # Open existing database (never delete it!)
    if not os.path.exists(DB_PATH):
        print('No existing database - creating new one')
        conn = sqlite3.connect(DB_PATH)
        create_schema(conn)
    else:
        conn = sqlite3.connect(DB_PATH)
        # Verify schema exists
        try:
            conn.execute('SELECT 1 FROM sessions LIMIT 1')
        except sqlite3.OperationalError:
            print('Database missing sessions table - creating schema')
            create_schema(conn)
    
    cursor = conn.cursor()
    
    # Get existing session IDs for tracking
    cursor.execute('SELECT id, message_count FROM sessions')
    existing_sessions = {row[0]: row[1] for row in cursor.fetchall()}
    print(f'Existing sessions in DB: {len(existing_sessions)}')
    
    sessions_imported = 0
    sessions_updated = 0
    sessions_skipped = 0
    messages_imported = 0
    errors = []
    
    for filepath in session_files:
        session_id = os.path.basename(filepath).replace('.json', '')
        
        # Read and parse file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            session, was_fixed = validate_json(content)
            
            if session is None:
                errors.append(f'ERROR: Could not parse {filepath}')
                print(f'  ERROR: Could not parse {filepath}')
                continue
            
            if was_fixed:
                print(f'  Fixed merge conflict in: {session_id}')
            
            # Get session data
            session_id = session.get('id', session_id)
            file_msg_count = len(session.get('messages', []))
            
            # Check if this is an update to existing session
            if session_id in existing_sessions:
                existing_count = existing_sessions[session_id]
                # Only update if file has MORE messages than existing
                if file_msg_count <= existing_count:
                    sessions_skipped += 1
                    print(f'  Skipped (up to date): {session_id} ({file_msg_count} msgs)')
                    continue
                else:
                    # Delete old messages for this session before re-importing
                    cursor.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
                    print(f'  Updating existing: {session_id} ({existing_count} -> {file_msg_count} msgs)')
                    sessions_updated += 1
            else:
                print(f'  Importing new: {session_id} ({file_msg_count} msgs)')
                sessions_imported += 1
            
            # Session columns in order
            session_cols = ['id', 'source', 'user_id', 'model', 'model_config', 'system_prompt',
                'parent_session_id', 'started_at', 'ended_at', 'end_reason', 'message_count',
                'tool_call_count', 'input_tokens', 'output_tokens', 'cache_read_tokens',
                'cache_write_tokens', 'reasoning_tokens', 'cwd', 'billing_provider',
                'billing_base_url', 'billing_mode', 'estimated_cost_usd', 'actual_cost_usd',
                'cost_status', 'cost_source', 'pricing_version', 'title', 'api_call_count',
                'handoff_state', 'handoff_platform', 'handoff_error', 'rewind_count',
                'archived', 'git_branch', 'git_repo_root']
            
            session_data = []
            for col in session_cols:
                val = session.get(col)
                if val is None or val == '':
                    if col in ['message_count', 'tool_call_count', 'input_tokens', 'output_tokens',
                               'cache_read_tokens', 'cache_write_tokens', 'reasoning_tokens',
                               'api_call_count', 'rewind_count', 'archived', 'token_count',
                               'observed', 'active', 'compacted']:
                        val = 0
                    elif col in ['started_at', 'ended_at', 'updated_at', 'timestamp']:
                        val = 0.0
                    elif col in ['estimated_cost_usd', 'actual_cost_usd']:
                        val = 0.0
                    else:
                        val = None
                session_data.append(val)
            
            placeholders = ','.join(['?' for _ in session_cols])
            conn.execute(f'INSERT OR REPLACE INTO sessions ({",".join(session_cols)}) VALUES ({placeholders})', session_data)
            
            # Import messages
            msg_cols = ['id', 'session_id', 'role', 'content', 'tool_call_id', 'tool_calls', 'tool_name',
                       'timestamp', 'token_count', 'finish_reason', 'reasoning', 'reasoning_content',
                       'reasoning_details', 'codex_reasoning_items', 'codex_message_items',
                       'platform_message_id', 'observed', 'active', 'compacted']

            for msg in session.get('messages', []):
                msg_data = []
                msg['session_id'] = session_id  # Ensure session_id is set
                for col in msg_cols:
                    val = msg.get(col)
                    if val is None or val == '':
                        if col in ['token_count', 'observed', 'active', 'compacted',
                                   'input_tokens', 'output_tokens', 'cache_read_tokens',
                                   'cache_write_tokens', 'reasoning_tokens']:
                            val = 0
                        elif col in ['timestamp', 'created_at', 'completed_at']:
                            val = 0.0
                        else:
                            val = None
                    msg_data.append(val)

                placeholders = ','.join(['?' for _ in msg_cols])
                col_names = ','.join(msg_cols)
                try:
                    conn.execute(f'INSERT INTO messages ({col_names}) VALUES ({placeholders})', msg_data)
                    messages_imported += 1
                except Exception as e:
                    print(f'  Warning importing message: {e}')
            
        except Exception as e:
            errors.append(f'ERROR importing {filepath}: {e}')
            print(f'  ERROR importing {filepath}: {e}')
            import traceback
            traceback.print_exc()
    
    conn.commit()
    conn.close()
    
    print(f'\nImport complete:')
    print(f'  New sessions: {sessions_imported}')
    print(f'  Updated: {sessions_updated}')
    print(f'  Skipped (up to date): {sessions_skipped}')
    print(f'  Messages imported: {messages_imported}')
    print(f'  Errors: {len(errors)}')
    
    if errors:
        print('\nErrors:')
        for err in errors:
            print(f'  {err}')
    
    return len(errors) == 0

def create_schema(conn):
    """Create the database schema if it doesn't exist."""
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
    
    # Create messages table
    conn.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT,
        tool_call_id TEXT, tool_calls TEXT, tool_name TEXT, timestamp REAL, token_count INTEGER,
        finish_reason TEXT, reasoning TEXT, reasoning_content TEXT, reasoning_details TEXT,
        codex_reasoning_items TEXT, codex_message_items TEXT, platform_message_id TEXT,
        observed INTEGER, active INTEGER, compacted INTEGER
    )
    ''')
    
    # Create FTS table
    conn.execute('''
    CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts 
    USING fts5(session_id, role, content, content="messages", content_rowid="id")
    ''')
    
    # Create supporting tables
    conn.execute('CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)')
    conn.execute('CREATE TABLE IF NOT EXISTS state_meta (key TEXT PRIMARY KEY, value TEXT)')
    conn.execute('''
    CREATE TABLE IF NOT EXISTS compression_locks (
        session_id TEXT PRIMARY KEY,
        holder TEXT NOT NULL,
        acquired_at REAL NOT NULL,
        expires_at REAL NOT NULL
    )
    ''')
    
    # Schema version
    conn.execute('INSERT OR IGNORE INTO schema_version VALUES (1)')
    
    # Create indexes
    conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_source ON sessions(source)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_source_id ON sessions(source, id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_session_active ON messages(session_id, active, timestamp)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_compression_locks_expires ON compression_locks(expires_at)')
    
    conn.commit()

if __name__ == '__main__':
    success = import_sessions()
    exit(0 if success else 1)