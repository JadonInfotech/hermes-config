#!/usr/bin/env python3
"""Export Hermes sessions from state.db to individual JSON files.
   Safe export that never deletes or overwrites existing sessions.
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

print(f'Hermes dir: {HERMES_DIR}')
print(f'DB path: {DB_PATH}')

def export_sessions():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    
    if not os.path.exists(DB_PATH):
        print('No state.db found')
        return True
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get sessions
    cursor.execute('SELECT * FROM sessions')
    sessions_cols = [desc[0] for desc in cursor.description]
    
    rows = cursor.fetchall()
    print(f'Found {len(rows)} sessions to export')
    
    exported = 0
    skipped = 0
    
    for row in rows:
        session = dict(zip(sessions_cols, row))
        session_id = session['id']
        
        # Safe filename
        safe_id = session_id.replace(':', '_').replace('-', '_').replace('.', '_')
        filepath = os.path.join(EXPORT_DIR, f'{safe_id}.json')
        
        # Check if we should skip (existing file is same or newer)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                # Skip if existing file has same or more messages (assumes it's up to date)
                existing_msg_count = len(existing.get('messages', []))
                new_msg_count = session.get('message_count', 0)
                if existing_msg_count >= new_msg_count and new_msg_count > 0:
                    # Also check if the message_count matches actual messages
                    cursor.execute('SELECT COUNT(*) FROM messages WHERE session_id = ?', (session_id,))
                    actual_count = cursor.fetchone()[0]
                    if existing_msg_count == actual_count:
                        skipped += 1
                        print(f"  Skipped (up to date): {session_id}")
                        continue
            except Exception as e:
                # File exists but is corrupted, we'll overwrite it
                print(f"  Re-exporting corrupted file: {session_id}")
        
        # Get messages for this session
        cursor.execute('SELECT * FROM messages WHERE session_id = ?', (session_id,))
        msg_cols = [desc[0] for desc in cursor.description]
        messages = []
        for msg_row in cursor.fetchall():
            msg = dict(zip(msg_cols, msg_row))
            # Convert None to empty string for JSON compatibility
            for k, v in msg.items():
                if v is None:
                    msg[k] = ''
            messages.append(msg)
        
        session['messages'] = messages
        session['exported_at'] = datetime.now().isoformat()
        session['exported_from'] = os.environ.get('COMPUTERNAME', 'unknown')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
        
        exported += 1
        print(f"  Exported: {session_id} ({len(messages)} messages)")
    
    conn.close()
    print(f'Successfully exported {exported} sessions, skipped {skipped} up-to-date')
    return True

if __name__ == '__main__':
    export_sessions()