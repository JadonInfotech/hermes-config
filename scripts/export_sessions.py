#!/usr/bin/env python3
"""Export Hermes sessions from state.db to individual JSON files.
   Safe export that never deletes or overwrites existing sessions.

   FIXED: Add machine prefix to session IDs to avoid cross-desktop conflicts.
"""

import sqlite3
import json
import os
import sys
import re
from datetime import datetime

# Get Hermes directory
HERMES_DIR = os.environ.get('LOCALAPPDATA', '') + '\\hermes'
if not HERMES_DIR or HERMES_DIR == '\\hermes':
    HERMES_DIR = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'hermes')

DB_PATH = os.path.join(HERMES_DIR, 'state.db')
EXPORT_DIR = os.path.join(HERMES_DIR, 'sync_sessions')
MACHINE_PREFIX = os.environ.get('COMPUTERNAME', 'UNKNOWN').upper()[:12]

print(f'Hermes dir: {HERMES_DIR}')
print(f'DB path: {DB_PATH}')
print(f'Machine prefix: {MACHINE_PREFIX}')

def make_sync_id(session_id, machine_prefix):
    """Create a collision-free sync ID: MACHINE_SESSIONID"""
    safe_session = session_id.replace(':', '_').replace('-', '_').replace('.', '_')
    return f'{machine_prefix}_{safe_session}'

def export_sessions():
    os.makedirs(EXPORT_DIR, exist_ok=True)

    if not os.path.exists(DB_PATH):
        print('No state.db found')
        return True

    # Check if DB is valid
    try:
        test_conn = sqlite3.connect(DB_PATH, timeout=1)
        test_conn.execute('SELECT 1 FROM sessions LIMIT 1')
        test_conn.close()
    except sqlite3.OperationalError as e:
        print(f'Database error: {e}')
        print('Is Hermes still running? Close Hermes and try again.')
        return False
    except sqlite3.DatabaseError as e:
        print(f'Database corrupted: {e}')
        print('The database file is not a valid SQLite database.')
        print('Try running: python scripts/repair_db.py')
        return False

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA query_only=ON')  # Read-only mode for safety
    cursor = conn.cursor()

    # Get sessions
    cursor.execute('SELECT * FROM sessions')
    sessions_cols = [desc[0] for desc in cursor.description]

    rows = cursor.fetchall()
    print(f'Found {len(rows)} sessions to export')

    exported = 0
    skipped = 0
    errors = 0

    for row in rows:
        session = dict(zip(sessions_cols, row))
        session_id = session['id']

        if not session_id:
            continue

        sync_id = make_sync_id(session_id, MACHINE_PREFIX)
        filepath = os.path.join(EXPORT_DIR, f'{sync_id}.json')

        # Get actual message count from messages table (safe way)
        cursor.execute('SELECT COUNT(*) FROM messages WHERE session_id = ?', (session_id,))
        actual_db_count = cursor.fetchone()[0] or 0

        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                existing_msg_count = len(existing.get('messages', []))
                existing_machine = existing.get('exported_from', '')

                # Skip if this machine already has an equal-or-better export
                if existing_machine == MACHINE_PREFIX and actual_db_count <= existing_msg_count:
                    skipped += 1
                    print(f"  Skipped (up to date): {sync_id}")
                    continue
            except Exception as e:
                print(f"  Re-exporting corrupted file: {sync_id} ({e})")

        # Get messages for this session
        cursor.execute('SELECT * FROM messages WHERE session_id = ?', (session_id,))
        msg_cols = [desc[0] for desc in cursor.description]
        messages = []
        for msg_row in cursor.fetchall():
            msg = dict(zip(msg_cols, msg_row))
            for k, v in msg.items():
                if v is None:
                    msg[k] = ''
            messages.append(msg)

        session['messages'] = messages
        session['exported_at'] = datetime.now().isoformat()
        session['exported_from'] = MACHINE_PREFIX
        session['original_session_id'] = session_id  # Store original for reference

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session, f, ensure_ascii=False, indent=2)
            exported += 1
            print(f"  Exported: {sync_id} ({len(messages)} messages)")
        except Exception as e:
            print(f"  ERROR exporting {sync_id}: {e}")
            errors += 1

    conn.close()
    print(f'Exported {exported} sessions, skipped {skipped} up-to-date, {errors} errors')
    return errors == 0

if __name__ == '__main__':
    success = export_sessions()
    sys.exit(0 if success else 1)