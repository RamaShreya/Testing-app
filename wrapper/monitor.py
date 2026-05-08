import time
import threading
import os
from session_manager import active_sessions
from reset import terminate_session
from logger_manager import session_logger, changes_logger

INACTIVITY_TIMEOUT = 30 * 60  # 30 minutes in seconds

# Dictionary to track file modification times per session
# session_id -> { file_path -> mtime }
file_states = {}

def monitor_sessions(target_session_id=None):
    """Continuously monitors active sessions, handles timeouts, and tracks file changes."""
    if target_session_id:
        from logger_manager import reconfigure_session_logging
        reconfigure_session_logging(target_session_id)
        
    print(f"Session monitor started{' for ' + target_session_id if target_session_id else ''}.")
    while True:
        current_time = time.time()
        sessions_to_terminate = []
        
        # Determine which sessions to monitor
        if target_session_id:
            if target_session_id not in active_sessions:
                # If target session is gone, monitor is done
                break
            sessions_to_check = [(target_session_id, active_sessions[target_session_id])]
        else:
            sessions_to_check = list(active_sessions.items())
            
        for session_id, data in sessions_to_check:
            # 1. Check for inactivity timeout
            time_since_last_activity = current_time - data['last_activity']
            if time_since_last_activity > INACTIVITY_TIMEOUT:
                print(f"Session {session_id} timed out due to inactivity.")
                session_logger.warning(f"Session {session_id} timed out after {time_since_last_activity} seconds of inactivity.")
                sessions_to_terminate.append(session_id)
                continue
                
            # 2. Health check: check if process is still running
            if data['process'] and data['process'].poll() is not None:
                print(f"Session {session_id} process died unexpectedly. Exit code: {data['process'].returncode}")
                session_logger.error(f"Session {session_id} process died unexpectedly. Exit code: {data['process'].returncode}")
                sessions_to_terminate.append(session_id)
                continue

            # 3. Track file modifications in runtime
            runtime_dir = data['runtime_dir']
            if os.path.exists(runtime_dir):
                if session_id not in file_states:
                    file_states[session_id] = {}
                    # Initial scan
                    for root, _, files in os.walk(runtime_dir):
                        for f in files:
                            path = os.path.join(root, f)
                            try:
                                file_states[session_id][path] = os.path.getmtime(path)
                            except OSError:
                                pass
                else:
                    current_files = set()
                    for root, _, files in os.walk(runtime_dir):
                        for f in files:
                            path = os.path.join(root, f)
                            current_files.add(path)
                            try:
                                mtime = os.path.getmtime(path)
                                if path not in file_states[session_id]:
                                    changes_logger.info(f"[{session_id}] File created: {path}")
                                    file_states[session_id][path] = mtime
                                elif mtime > file_states[session_id][path]:
                                    changes_logger.info(f"[{session_id}] File modified: {path}")
                                    file_states[session_id][path] = mtime
                            except OSError:
                                pass
                    
                    # Check for deletions
                    for old_path in list(file_states[session_id].keys()):
                        if old_path not in current_files:
                            changes_logger.warning(f"[{session_id}] File deleted: {old_path}")
                            del file_states[session_id][old_path]

        # Terminate dead or timed-out sessions
        for session_id in sessions_to_terminate:
            terminate_session(session_id)
            if session_id in file_states:
                del file_states[session_id]
            
        time.sleep(10)  # Check every 10 seconds for faster feedback

def start_monitor(session_id=None):
    monitor_thread = threading.Thread(target=monitor_sessions, args=(session_id,), daemon=True)
    monitor_thread.start()
    return monitor_thread

if __name__ == "__main__":
    start_monitor()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Monitor shutting down...")
