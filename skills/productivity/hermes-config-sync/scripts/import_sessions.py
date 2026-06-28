#!/usr/bin/env python3
"""Import Hermes sessions from JSON files back into state.db."""

import sqlite3
import json
import os
import glob
import subprocess

HERMES_DIR = os.environ.get('LOCALAPPDATA', '') + '\\hermes'
if not HERMES_DIR or HERMES_DIR == '\\hermes':
    HERMES_DIR = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'hermes')

DB_PATH = os.path.join(HERMES_DIR, 'state.db')
EXPORT_DIR = os.path.join(HERMES_DIR, 'sync_sessions')


def import_sessions():
    session_files = glob.glob(os.path.join(EXPORT_DIR, '*.json'))
    print(f'Found {len(session_files)} session files to import')

    if not session_files:
        print('No sessions to import')
        return True

    result = subprocess.run(['tasklist'], capture_output=True, text=True)
    if 'Hermes.exe' in result.stdout:
        print('WARNING: Hermes is running! Close Hermes first for full import.')
        print('Sessions are synced to GitHub - will import when Hermes is closed.')
        return True

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

    sessions_imported = 0
    messages_imported = 0

    for filepath in session_files:
        try:
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

            conn.execute(f'INSERT OR REPLACE INTO sessions VALUES ({",".join(["?"]*35)})', session_data)
            sessions_imported += 1

            msg_cols = ['session_id', 'role', 'content', 'tool_call_id', 'tool_calls', 'tool_name',
                       'timestamp', 'token_count', 'finish_reason', 'reasoning', 'reasoning_content',
                       'reasoning_details', 'codex_reasoning_items', 'codex_message_items',
                       'platform_message_id', 'observed', 'active', 'compacted']

            for msg in session.get('messages', []):
                msg['session_id'] = session_id
                msg_data = []
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
                try:
                    conn.execute(f'INSERT INTO messages VALUES ({",".join(["?"]*18)})', msg_data)
                    messages_imported += 1
                except Exception as e:
                    print(f'  Error importing message: {e}')

            print(f"  Imported: {session_id} ({len(session.get('messages', []))} messages)")

        except Exception as e:
            print(f'  ERROR importing {filepath}: {e}')

    conn.commit()
    conn.close()

    print(f'Imported {sessions_imported} sessions, {messages_imported} messages')
    os.rename(new_db, DB_PATH)

    for ext in ['-shm', '-wal']:
        wal_path = DB_PATH + ext
        if os.path.exists(wal_path):
            os.remove(wal_path)

    print('Database rebuilt successfully!')
    return True


if __name__ == '__main__':
    import_sessions()
