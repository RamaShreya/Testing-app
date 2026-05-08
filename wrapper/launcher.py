import os
import sys
import shutil
import uuid
import subprocess
import time
import socket
import urllib.request
import webbrowser
import psutil
from logger_manager import session_logger
from session_manager import register_session, update_session_status, active_sessions, sync_from_disk

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def wait_for_server(url, timeout=30):
    start_time = time.time()
    print(f"Waiting for server at {url} to become reachable...")
    while time.time() - start_time < timeout:
        try:
            response = urllib.request.urlopen(url)
            if response.getcode() == 200:
                print("Server is reachable!")
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def create_session():
    """Creates a new isolated runtime session with hardening."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_dir = os.path.join(base_dir, 'source_app')
    venv_python = os.path.join(base_dir, 'venv', 'Scripts', 'python.exe')
    
    if not os.path.exists(venv_python):
        venv_python = sys.executable

    print("\n" + "="*50)
    print("VULNERABLE LAB LAUNCHER")
    print("="*50)

    # 0. Check for existing active sessions (Optional: could warn if too many)
    sync_from_disk()

    session_id = f"session_{uuid.uuid4().hex[:8]}"
    runtime_dir = os.path.join(base_dir, 'runtime', session_id)
    # Isolated logs directory
    log_dir = os.path.join(base_dir, 'logs', session_id)
    os.makedirs(log_dir, exist_ok=True)

    # Reconfigure loggers to point to session-specific directory
    from logger_manager import reconfigure_session_logging
    reconfigure_session_logging(session_id)

    print(f"[*] Generating new session: {session_id}")
    session_logger.info(f"Starting new session: {session_id}")
    
    # 1. Ensure runtime directory doesn't exist
    if os.path.exists(runtime_dir):
        def remove_readonly(func, path, excinfo):
            import stat
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(runtime_dir, onerror=remove_readonly)
        
    # 2. Copy source to runtime
    try:
        shutil.copytree(source_dir, runtime_dir)
        print(f"[*] Created isolated runtime: {runtime_dir}")
        session_logger.info(f"Copied source_app to {runtime_dir}")
    except Exception as e:
        print(f"[!] Failed to copy source app: {e}")
        session_logger.error(f"Failed to copy source app: {e}")
        return None
        
    # 3. Launch Flask
    port = get_free_port()
    url = f"http://127.0.0.1:{port}"
    
    env = os.environ.copy()
    env['LAB_SESSION_ID'] = session_id
    env['LAB_LOG_DIR'] = log_dir
    env['LAB_PORT'] = str(port)
    env['FLASK_DEBUG'] = '0' # Disable reloader
    
    print(f"[*] Starting Flask server on {url} (Reloader Disabled)...")
    try:
        process = subprocess.Popen(
            [venv_python, "app.py"],
            cwd=runtime_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        
        session_data = {
            'process': process,
            'pid': process.pid,
            'runtime_dir': runtime_dir,
            'port': port,
            'url': url,
            'start_time': time.time(),
            'last_activity': time.time()
        }
        register_session(session_id, session_data)
        
        session_logger.info(f"Session {session_id} initialized. URL: {url}, PID: {process.pid}")
        
        if wait_for_server(url):
            update_session_status(session_id, 'active')
            print("\n" + "="*50)
            print("LAB ENVIRONMENT READY!")
            print(f"Access URL: {url}")
            print(f"Session ID: {session_id}")
            print("="*50 + "\n")
            
            webbrowser.open(url)
            
            from monitor import start_monitor
            start_monitor(session_id)
            
            return session_id
        else:
            print(f"[!] Server failed to start.")
            session_logger.error(f"Session {session_id} unreachable.")
            from reset import terminate_session
            terminate_session(session_id)
            return None
            
    except Exception as e:
        print(f"[!] Launch failed: {e}")
        session_logger.error(f"Launch failed for {session_id}: {e}")
        return None

if __name__ == "__main__":
    # Crash Recovery: Clean orphaned runtime folders on startup
    print("[*] Performing startup crash recovery check...")
    sync_from_disk()
    runtime_root = os.path.join(os.getcwd(), 'runtime')
    if os.path.exists(runtime_root):
        from reset import terminate_session
        for item in os.listdir(runtime_root):
            if item.startswith('session_'):
                if item not in active_sessions:
                    print(f"[*] Found orphaned session {item}, cleaning up...")
                    item_path = os.path.join(runtime_root, item)
                    def remove_readonly(func, path, excinfo):
                        import stat
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    shutil.rmtree(item_path, onerror=remove_readonly, ignore_errors=True)
                else:
                    # Check if session process is actually alive
                    data = active_sessions[item]
                    pid = data.get('pid')
                    if not pid or not psutil.pid_exists(pid):
                        print(f"[*] Found stale session {item}, cleaning up...")
                        terminate_session(item)

    session_id = create_session()
    if session_id:
        print("[*] Press Ctrl+C to terminate session and cleanup.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Shutting down session...")
            from reset import terminate_session
            terminate_session(session_id)
            print("[*] Cleanup complete.")
