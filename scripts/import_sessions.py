#!/usr/bin/env python3
"""Import Hermes sessions from JSON files back into state.db."""

import sqlite3
import json
import os
import glob
from datetime import datetime

# Fixed path - Hermes config directory
HERMES_DIR = os.environ.get('LOCALAPPDATA', os.path.expanduser('~')) + "\\hermes"
DB_PATH = os.path.join(HERMES_DIR, "state.db")
EXPORT_DIR = os.path.join(HERMES_DIR, "sync_sessions")

def import_sessions():
    session_files = glob.glob(os.path.join(EXPORT_DIR, "*.json"))
    print(f"Found {len(session_files)} session files to import")
    
    if not session_files:
        print("No sessions to import - keeping existing database")
        return True
    
    # Create new database
    new_db = os.path.join(HERMES_DIR, "state_new.db")
    if os.path.exists(new_db):
        os.remove(new_db)
    
    conn = sqlite3.connect(new_db)
    
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
        tool_calls TEXT, tool_result TEXT, model TEXT, provider TEXT, input_tokens INTEGER,
        output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER,
        reasoning_tokens INTEGER, created_at REAL, completed_at REAL, error TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )
    ''')
    
    # Create FTS table
    conn.execute('''
    CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts 
    USING fts5(session_id, role, content, content="messages", content_rowid="id")
    ''')
    
    # Create supporting tables
    conn.execute('CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)')
    conn.execute('CREATE TABLE IF NOT EXISTS state_meta (key TEXT PRIMARY KEY, value TEXT, updated_at REAL)')
    conn.execute('CREATE TABLE IF NOT EXISTS sqlite_sequence (name TEXT, seq INTEGER)')
    conn.execute('CREATE TABLE IF NOT EXISTS compression_locks (session_id TEXT PRIMARY KEY)')
    
    # Schema version
    conn.execute('INSERT INTO schema_version VALUES (1)')
    
    # Import each session
    sessions_imported = 0
    messages_imported = 0
    
    session_cols = ['id', 'source', 'user_id', 'model', 'model_config', 'system_prompt',
        'parent_session_id', 'started_at', 'ended_at', 'end_reason', 'message_count',
        'tool_call_count', 'input_tokens', 'output_tokens', 'cache_read_tokens',
        'cache_write_tokens', 'reasoning_tokens', 'cwd', 'billing_provider',
        'billing_base_url', 'billing_mode', 'estimated_cost_usd', 'actual_cost_usd',
        'cost_status', 'cost_source', 'pricing_version', 'title', 'api_call_count',
        'handoff_state', 'handoff_platform', 'handoff_error', 'rewind_count',
        'archived', 'git_branch', 'git_repo_root']
    
    msg_cols = ['session_id', 'role', 'content', 'tool_calls', 'tool_result',
               'model', 'provider', 'input_tokens', 'output_tokens', 'cache_read_tokens',
               'cache_write_tokens', 'reasoning_tokens', 'created_at', 'completed_at', 'error']
    
    for filepath in session_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                session = json.load(f)
            
            # Extract session data
            session_data = []
            for col in session_cols:
                val = session.get(col)
                if val is None:
                    if col in ['message_count', 'tool_call_count', 'input_tokens', 'output_tokens',
                               'cache_read_tokens', 'cache_write_tokens', 'reasoning_tokens',
                               'api_call_count', 'rewind_count', 'archived']:
                        val = 0
                    elif col in ['started_at', 'ended_at', 'updated_at', 'created_at', 'completed_at']:
                        val = 0.0
                    elif col in ['estimated_cost_usd', 'actual_cost_usd']:
                        val = 0.0
                    else:
                        val = None
                session_data.append(val)
            
            placeholders = ','.join(['?' for _ in session_cols])
            conn.execute(f'INSERT OR REPLACE INTO sessions VALUES ({placeholders})', session_data)
            sessions_imported += 1
            
            # Import messages
            for msg in session.get('messages', []):
                msg_data = []
                for col in msg_cols:
                    val = msg.get(col)
                    if val is None:
                        if col in ['input_tokens', 'output_tokens', 'cache_read_tokens',
                                   'cache_write_tokens', 'reasoning_tokens']:
                            val = 0
                        elif col in ['created_at', 'completed_at']:
                            val = 0.0
                        else:
                            val = None
                    msg_data.append(val)
                
                placeholders = ','.join(['?' for _ in msg_cols])
                conn.execute(f'INSERT INTO messages VALUES ({placeholders})', msg_data)
                messages_imported += 1
            
            print(f"  Imported: {session.get('id', 'unknown')} ({len(session.get('messages', []))} messages)")
            
        except Exception as e:
            print(f"  ERROR importing {filepath}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"Imported {sessions_imported} sessions, {messages_imported} messages")
    
    # Replace old database
    if os.path.exists(DB_PATH):
        backup = DB_PATH + ".backup"
        if os.path.exists(backup):
            os.remove(backup)
        os.rename(DB_PATH, backup)
    
    os.rename(new_db, DB_PATH)
    
    if os.path.exists(DB_PATH + ".backup"):
        os.remove(DB_PATH + ".backup")
    
    print(f"Database rebuilt successfully!")
    return True

if __name__ == "__main__":
    import_sessions()