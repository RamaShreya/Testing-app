import json
import os
import time
import tempfile

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'active_sessions.json')

def load_sessions():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_sessions(sessions):
    """Atomic write to prevent corruption."""
    serializable = {}
    for sid, data in sessions.items():
        serializable[sid] = {k: v for k, v in data.items() if k != 'process'}
    
    try:
        # Create a temp file in the same directory to ensure atomic rename
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(SESSION_FILE), prefix='sessions_', suffix='.tmp', text=True)
        with os.fdopen(fd, 'w') as f:
            json.dump(serializable, f, indent=4)
        
        # Replace the original file with the new one atomically
        if os.path.exists(SESSION_FILE):
            os.replace(temp_path, SESSION_FILE)
        else:
            os.rename(temp_path, SESSION_FILE)
    except Exception as e:
        print(f"[ERROR] Registry write failed: {e}")
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

# Global memory registry
active_sessions = {}

def register_session(session_id, data):
    """Registers a session with status tracking."""
    sync_from_disk()
    data['status'] = 'starting'
    active_sessions[session_id] = data
    save_sessions(active_sessions)
    print(f"[DEBUG] Session {session_id} registered (Status: starting)")

def update_session_status(session_id, status):
    """Updates session status (active/stopped/cleaning/resetting)."""
    sync_from_disk()
    if session_id in active_sessions:
        active_sessions[session_id]['status'] = status
        save_sessions(active_sessions)
        print(f"[DEBUG] Session {session_id} status changed to: {status}")

def unregister_session(session_id):
    sync_from_disk()
    if session_id in active_sessions:
        active_sessions[session_id]['status'] = 'cleaning'
        save_sessions(active_sessions)
        del active_sessions[session_id]
        save_sessions(active_sessions)
        print(f"[DEBUG] Session {session_id} unregistered from disk.")

def sync_from_disk():
    """Synchronizes the global active_sessions registry with the disk file."""
    disk_sessions = load_sessions()
    
    # Remove sessions that are no longer on disk
    for sid in list(active_sessions.keys()):
        if sid not in disk_sessions:
            del active_sessions[sid]
            
    # Add or update sessions from disk
    for sid, data in disk_sessions.items():
        if sid not in active_sessions:
            active_sessions[sid] = data
            active_sessions[sid]['process'] = None
        else:
            # Preserve local process object but update other metadata
            local_proc = active_sessions[sid].get('process')
            active_sessions[sid].update(data)
            active_sessions[sid]['process'] = local_proc
            
    return active_sessions

# Auto-sync on import
sync_from_disk()
