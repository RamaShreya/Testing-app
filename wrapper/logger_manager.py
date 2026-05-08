import logging
import os

def setup_logger(name, log_file, level=logging.INFO):
    """Function setup as many loggers as you want"""
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Ensure logs directory exists
    log_dir = os.environ.get('LAB_LOG_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs'))
    os.makedirs(log_dir, exist_ok=True)
    
    file_path = os.path.join(log_dir, log_file)
    handler = logging.FileHandler(file_path)        
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent adding handlers multiple times
    if not logger.handlers:
        logger.addHandler(handler)

    return logger

def reconfigure_session_logging(session_id):
    """Redirects all centralized loggers to a session-specific directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, 'logs', session_id)
    os.makedirs(log_dir, exist_ok=True)
    
    # Update environment variable for consistency
    os.environ['LAB_LOG_DIR'] = log_dir
    
    loggers = {
        'access': 'access.log',
        'auth': 'auth.log',
        'attack': 'attack.log',
        'changes': 'changes.log',
        'session': 'session.log'
    }
    
    for name, log_file in loggers.items():
        logger = logging.getLogger(name)
        # Clear existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add new handler
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_path = os.path.join(log_dir, log_file)
        handler = logging.FileHandler(file_path)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return log_dir

# Centralized loggers
access_logger = setup_logger('access', 'access.log')
auth_logger = setup_logger('auth', 'auth.log')
attack_logger = setup_logger('attack', 'attack.log')
changes_logger = setup_logger('changes', 'changes.log')
session_logger = setup_logger('session', 'session.log')

print("[VERIFY] Log handlers attached and initialized.")
