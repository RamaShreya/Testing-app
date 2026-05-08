import os
import shutil
import subprocess
from logger_manager import session_logger
from session_manager import active_sessions

def terminate_session(session_id):
    """Destroys a runtime session completely."""
    from logger_manager import reconfigure_session_logging
    reconfigure_session_logging(session_id)
    
    if session_id not in active_sessions:
        print(f"Session {session_id} not found.")
        return False
        
    session = active_sessions[session_id]
    pid = session.get('pid')
    runtime_dir = session.get('runtime_dir')
    
    # Try to get process object if missing
    process = session.get('process')

    print(f"Terminating session: {session_id} (PID: {pid})")
    session_logger.info(f"Terminating session: {session_id} (PID: {pid})")
    
    # 1. Stop the process
    try:
        if pid:
            if os.name == 'nt':
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(pid)])
            else:
                os.kill(pid, 15)
        elif process:
            process.terminate()
    except Exception as e:
        print(f"Warning: Could not terminate process {pid}: {e}")
            
    # 2. Delete the runtime directory completely
    try:
        if os.path.exists(runtime_dir):
            def remove_readonly(func, path, excinfo):
                import stat
                os.chmod(path, stat.S_IWRITE)
                func(path)

            shutil.rmtree(runtime_dir, onerror=remove_readonly)
            print(f"Deleted runtime directory: {runtime_dir}")
            session_logger.info(f"Deleted runtime directory: {runtime_dir}")
    except Exception as e:
        print(f"Failed to delete runtime directory {runtime_dir}: {e}")
        session_logger.error(f"Failed to delete runtime directory {runtime_dir}: {e}")
        
    # 3. Remove from active sessions
    from session_manager import unregister_session
    unregister_session(session_id)
    return True
def terminate_all_sessions():
    """Terminates all active sessions and cleans up all runtime directories."""
    from session_manager import sync_from_disk
    sync_from_disk()
    
    sids = list(active_sessions.keys())
    if not sids:
        print("No active sessions found in registry.")
    else:
        print(f"Terminating {len(sids)} sessions...")
        for sid in sids:
            terminate_session(sid)
            
    # Final sweep of the runtime directory for any orphans
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runtime_base = os.path.join(base_dir, 'runtime')
    if os.path.exists(runtime_base):
        for item in os.listdir(runtime_base):
            item_path = os.path.join(runtime_base, item)
            if os.path.isdir(item_path):
                print(f"Force cleaning orphaned runtime: {item_path}")
                try:
                    def remove_readonly(func, path, excinfo):
                        import stat
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    shutil.rmtree(item_path, onerror=remove_readonly, ignore_errors=True)
                except Exception as e:
                    print(f"Failed to clean {item_path}: {e}")

    return True

if __name__ == "__main__":
    import sys
    from session_manager import sync_from_disk
    # Ensure we have the latest state from disk
    active_sessions = sync_from_disk()
    
    if len(sys.argv) > 1:
        if sys.argv[1].lower() == 'all':
            terminate_all_sessions()
        else:
            terminate_session(sys.argv[1])
    else:
        print("Usage: python reset.py <session_id | all>")
        print("Example: python reset.py all")
