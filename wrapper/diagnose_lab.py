import os
import sys
import logging
import json
import psutil
import socket
import time

# Add wrapper to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wrapper'))

def check_structure():
    print("[*] Checking directory structure...")
    dirs = ['source_app', 'runtime', 'logs', 'wrapper']
    for d in dirs:
        exists = os.path.exists(d)
        print(f"  {d:12}: {'EXISTS' if exists else 'MISSING'}")

def check_registry():
    print("\n[*] Checking session registry health...")
    from session_manager import SESSION_FILE, load_sessions
    if os.path.exists(SESSION_FILE):
        sessions = load_sessions()
        print(f"  Registered sessions: {len(sessions)}")
        for sid, data in sessions.items():
            pid = data.get('pid')
            status = data.get('status', 'unknown')
            port = data.get('port')
            
            print(f"    [{sid}] Status: {status}, PID: {pid}, Port: {port}")
            
            # Verify PID
            if pid:
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    print(f"      [OK] Process alive: {proc.name()} (Created: {time.ctime(proc.create_time())})")
                else:
                    print(f"      [FAIL] Process {pid} is DEAD but registered as {status}")
            
            # Verify Port
            if port:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(('127.0.0.1', port))
                    if result == 0:
                        print(f"      [OK] Port {port} is reachable")
                    else:
                        print(f"      [FAIL] Port {port} is NOT reachable")
            
            # Verify Directory
            rdir = data.get('runtime_dir')
            if rdir and os.path.exists(rdir):
                print(f"      [OK] Runtime directory exists")
            else:
                print(f"      [FAIL] Runtime directory MISSING")
    else:
        print("  Registry file MISSING.")

def check_orphans():
    print("\n[*] Checking for orphaned runtime folders...")
    from session_manager import load_sessions
    sessions = load_sessions()
    runtime_root = os.path.join(os.getcwd(), 'runtime')
    if os.path.exists(runtime_root):
        for item in os.listdir(runtime_root):
            if item.startswith('session_') and item not in sessions:
                print(f"  [ORPHAN] Found directory {item} without registry entry.")

def check_source_protection():
    print("\n[*] Verifying source_app protection...")
    source_dir = os.path.join(os.getcwd(), 'source_app')
    # Check if we can write to a file in source_app (should be read-only on Windows if attrib +r was used)
    test_file = os.path.join(source_dir, 'app.py')
    if os.path.exists(test_file):
        import stat
        mode = os.stat(test_file).st_mode
        if not (mode & stat.S_IWUSR):
            print(f"  [OK] source_app/app.py is Read-Only")
        else:
            print(f"  [WARNING] source_app/app.py is WRITABLE")

if __name__ == "__main__":
    print("="*60)
    print("VULNERABLE LAB - ADVANCED HEALTH VALIDATION")
    print("="*60)
    check_structure()
    check_registry()
    check_orphans()
    check_source_protection()
    print("="*60)
