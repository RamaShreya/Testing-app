# Vulnerable E-Commerce Cyber Lab

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-3.0-green)](https://flask.palletsprojects.com/)
[![Status](https://img.shields.io/badge/status-active-success.svg)](#)

## Project Overview

**Vulnerable E-Commerce Cyber Lab** is a dual-purpose web application designed to function both as a production-grade electronics storefront and a highly interactive, intentionally exploitable Security Learning Lab. 

Built with Flask, the platform features a dynamic session-based architecture that creates isolated runtime environments for each user. It incorporates a unique **Vulnerability Toggle (`VULN_MODE`)** that allows users to seamlessly switch between a hardened, secure application and a vulnerable state. This allows security professionals, students, and developers to safely practice exploiting real-world vulnerabilities (like SQL Injection, XSS, and IDOR) and immediately compare them against secure, patched implementations.

---

## Features

- **Dual State Execution**: Seamlessly toggle between "Secure Mode" (patched) and "Training Mode" (vulnerable) to understand both the exploit and the mitigation.
- **Isolated Sandbox Sessions**: The wrapper infrastructure automatically generates a disposable, isolated runtime (`runtime/session_xyz`) and a dedicated port for every launch, preventing multi-user interference.
- **Comprehensive Vulnerability Labs**: Pre-built modules demonstrating OWASP Top 10 vulnerabilities.
- **Advanced Forensic Logging**: Isolated, per-session log files for Access, Authentication, Attack payloads, and System Changes to trace exploitation paths.
- **Fully Functional E-Commerce Storefront**: Complete with product searching, categorization, shopping cart, mock checkout, and user accounts.
- **Automated Teardown**: Built-in crash recovery and cleanup routines to securely destroy environments upon exit.

---

## Technologies Used

### Backend & Core
- **Python 3.8+**: Core programming language.
- **Flask**: Web framework for routing and application logic.
- **Flask-SQLAlchemy**: ORM for database interactions.
- **Flask-Login**: Session management and user authentication.
- **Werkzeug**: Security hashing and file handling utilities.

### Frontend
- **HTML5 / CSS3**: Structure and styling.
- **Jinja2**: Dynamic HTML templating engine.

### Infrastructure & Management
- **SQLite**: Lightweight database utilized per session.
- **psutil / subprocess**: Process management for concurrent session handling.
- **Custom Wrapper Scripts**: Python infrastructure for dynamic provisioning and teardown.

---

## Project Architecture

The project separates the static, read-only codebase from ephemeral, executing instances:

1. **Source App (`source_app/`)**: The master blueprint of the web application. This directory remains read-only to preserve the integrity of the lab.
2. **Wrapper Infrastructure (`wrapper/`)**: Scripts responsible for orchestrating the environment. It provisions free ports, clones the source into a temporary runtime, attaches specific loggers, and spawns the Flask process.
3. **Runtime (`runtime/`)**: Ephemeral directories holding the actively running code and SQLite databases for each session.
4. **Logging System (`logs/`)**: Centralized directory capturing separated streams (auth, attack, etc.) mapped to specific session IDs.

---

## Folder Structure

```text
vulnerable_app/
├── backups/                 # System and database backups
├── logs/                    # Forensic log outputs (separated by session ID)
├── runtime/                 # Ephemeral, isolated session environments
├── source_app/              # Core application blueprint (read-only)
│   ├── instance/            # SQLite database storage
│   ├── static/              # CSS, JS, images, and user uploads/downloads
│   ├── templates/           # Jinja2 HTML templates
│   ├── app.py               # Main Flask application and route definitions
│   ├── models.py            # SQLAlchemy database schemas
│   └── requirements.txt     # Python dependencies
├── wrapper/                 # Infrastructure and environment orchestration
│   ├── active_sessions.json # Registry tracking live sessions
│   ├── diagnose_lab.py      # Diagnostic and health-check utilities
│   ├── launcher.py          # Session creation and server bootstrap
│   ├── logger_manager.py    # Multi-channel forensic log handling
│   ├── monitor.py           # Watchdog for session activity
│   ├── reset.py             # Session teardown, kill switches, and cleanup
│   └── session_manager.py   # State and configuration management for sessions
└── Procfile                 # Deployment configuration
```

---

## Installation Guide

Follow these steps to set up the lab environment on your local machine:

**1. Clone the repository**
```bash
git clone https://github.com/yourusername/vulnerable-cyber-lab.git
cd vulnerable-cyber-lab
```

**2. Create a Virtual Environment**
```bash
python -m venv venv
```

**3. Activate the Virtual Environment**
- **Windows**:
  ```cmd
  venv\Scripts\activate
  ```
- **macOS / Linux**:
  ```bash
  source venv/bin/activate
  ```

**4. Install Dependencies**
```bash
pip install -r source_app/requirements.txt
```

---

## Usage Instructions

**1. Launch the Environment**
Start the lab using the launcher wrapper rather than running `app.py` directly. This ensures session isolation.
```bash
python wrapper/launcher.py
```

**2. Access the Application**
The launcher will automatically find an available port, spawn an isolated environment, and open your default web browser to the dynamically generated URL (e.g., `http://127.0.0.1:54321`).

**3. Explore and Exploit**
- Browse the mock e-commerce store.
- Click **"Toggle Vulnerability Mode"** in the navigation bar to enable vulnerabilities.
- Navigate to the **Lab** section (`/lab`) to practice specific exploits.

**4. Graceful Shutdown**
In the terminal running the launcher, press `Ctrl+C`. The wrapper will automatically terminate the Flask process and scrub the temporary `runtime/` files.

---

## Environment Variables

While the wrapper handles dynamic configuration, the underlying application utilizes the following variables:
- `LAB_SESSION_ID`: Unique identifier for the active session.
- `LAB_LOG_DIR`: Target directory for forensic logs.
- `LAB_PORT`: Assigned port for the runtime instance.
- `FLASK_DEBUG`: Toggled dynamically by the launcher to control the Werkzeug reloader.

---

## Requirements

- **Python 3.8** or higher
- **Standard Library Modules**: `os`, `sys`, `shutil`, `subprocess`, `uuid`, `socket`, `sqlite3`
- Third-party packages listed in `requirements.txt` (Flask, SQLAlchemy, psutil, etc.)

---

## Authentication Flow

The application features a dual-state authentication flow:
- **Secure Mode**: Utilizes `Flask-Login` for session management and `werkzeug.security` (`generate_password_hash`, `check_password_hash`) to safely salt and hash passwords.
- **Vulnerable Mode (Training)**: Purposefully bypasses secure checks. It allows plain-text password comparison against the database hash, or a hardcoded universal backdoor bypass (e.g., authenticating with `"password123"` regardless of the user).

---

## Database Information

The project uses a local **SQLite** database (`database.db`) automatically generated inside the isolated `runtime/` directory upon launch. 

### Core Models:
- **User**: Stores user credentials, hashes, and roles.
- **Product**: E-commerce inventory catalog.
- **Order**: Order history linked to users.
- **LabReview**: User-submitted reviews (used for Stored XSS demonstrations).
- **Coupon**: Discount codes (used for Business Logic flaw demonstrations).

The database is automatically seeded on startup with sample products, simulated orders, and default accounts (`admin:admin123` and `guest:guest123`).

---

## API Endpoints

### Core Application
- `GET /` - Main Storefront / Product Search
- `GET /product/<id>` - Product Details
- `GET/POST /login` - User Authentication
- `GET/POST /register` - User Registration
- `GET /logout` - Terminate Session
- `GET /toggle-vuln` - Toggle the global `VULN_MODE` flag

### Store & Cart
- `GET /cart` - View Shopping Cart
- `GET /add_to_cart/<id>` - Add Item to Cart
- `GET /remove_from_cart/<id>` - Remove Item from Cart
- `GET/POST /checkout` - Process Dummy Checkout

### Vulnerability Labs
- `GET /lab` - Index of all interactive modules
- `GET/POST /lab/sqli` - SQL Injection Simulation
- `GET/POST /lab/xss` - Reflected Cross-Site Scripting
- `GET/POST /lab/stored-xss` - Stored Cross-Site Scripting
- `GET /orders/<id>` - Insecure Direct Object Reference (IDOR)
- `GET /lab/download` - Directory Traversal / Path Traversal
- `GET/POST /lab/upload` - Unrestricted File Upload
- `GET/POST /lab/business-logic` - Coupon / Business Logic Flaws
- `GET/POST /lab/brute-force` - Brute Force Authentication
- `GET /lab/redirect` - Open Redirects
- `GET /lab/info-disclosure` - Environment Information Disclosure

---

## Logging and Monitoring

A robust, multi-channel logging system (`logger_manager.py`) is implemented to act as an IDS/Forensic tool. Logs are uniquely tied to the `LAB_SESSION_ID` and stored in `logs/session_<id>/`.

- **Access Log**: Tracks all standard HTTP requests and IPs.
- **Auth Log**: Monitors successful logins, failed attempts, and brute-force indicators.
- **Attack Log**: Explicitly captures malicious payloads detected by the application (e.g., `<script>` tags, raw SQL queries, directory traversal patterns).
- **Changes Log**: Monitors structural modifications and file system interactions within the runtime.

---

## Security Notice

> **⚠️ CRITICAL WARNING ⚠️**
> 
> **This application is INTENTIONALLY VULNERABLE to severe security threats (SQLi, XSS, RCE, IDOR, etc.).** 
> It is designed **strictly** for educational purposes, ethical hacking practice, and local cybersecurity training. 
> 
> **DO NOT** deploy this application to a production server. **DO NOT** expose this application to the public internet. Run it solely within an isolated local environment or dedicated private sandbox. The authors are not responsible for any misuse or damage caused by this software.

---

## Screenshots

| Home Page | login | cart |
|:---:|:---:|:---:|
| ![Home]() | ![login](screenshots/dashboard.png) | ![cart](screenshots/exploit.png) |

---

## Future Improvements

- **Docker Containerization**: Migrate from Python virtual environments to Docker containers for stricter resource limitations and security isolation.
- **CTF Gamification**: Integrate a flag-scoring system to gamify the learning experience.
- **Advanced Modules**: Add labs for Server-Side Request Forgery (SSRF), XML External Entities (XXE), and Insecure Deserialization.
- **Automated Exploitation Tests**: Implement integration scripts to demonstrate automated exploitation (e.g., sqlmap integration tests).

---

## Troubleshooting

- **Orphaned Sessions / Server Won't Start**: If the application crashed previously, stale runtime folders might exist. The launcher usually cleans these up, but you can manually run `python wrapper/reset.py` or delete the contents of the `runtime/` folder.
- **Database Errors on Login**: Ensure you are running the app via `launcher.py` and not executing `app.py` directly, as the working directory must be handled correctly for SQLite to initialize.
- **Cannot see Logs**: Ensure the `logs/` directory has write permissions and the session ID matches your currently running instance.

---

## Contributing

Contributions to improve the labs, add new vulnerabilities, or enhance the documentation are highly encouraged!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/NewVulnerability`)
3. Commit your Changes (`git commit -m 'Add new SSRF lab module'`)
4. Push to the Branch (`git push origin feature/NewVulnerability`)
5. Open a Pull Request

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

---

## Author

**Security Development Team**
- GitHub: @RamaShreya
- Project Link: https://github.com/RamaShreya/Testing-app 
