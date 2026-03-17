<div align="center">

# Integrated Share

<img src="./assets/Banner.jpg" alt="Integrated Share Banner" width="100%" />

**A self-hosted local file sharing app built by students, for students (and honestly, for any small network setup).**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3-000000?style=flat&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)
![Visitors](https://visitor-badge.laobi.icu/badge?page_id=InferiorAK.Integrated-Share)

*Team 0xTJRS23*

</div>

---

## What this project is

<img src="./assets/Project_Mechanism.png" alt="Proof 1 - Register" width="100%" />

This is a web app where one machine hosts the server and everyone else on the same reachable network can upload, manage, and share files from a browser.

Even though registration format is `@student.ruet.ac.bd`, the app itself is not locked to RUET campus Wi-Fi only. You can run it on home Wi-Fi, lab LAN, or private WAN too.

---

## Quick Proof of Concept

<img src="./assets/1. Register.png" alt="Proof 1 - Register" width="100%" />
<img src="./assets/2. Login.png" alt="Proof 2 - Login" width="100%" />
<img src="./assets/3. Sharing Application Interface.png" alt="Proof 3 - Sharing App UI" width="100%" />
<img src="./assets/4. Profile.png" alt="Proof 4 - Profile" width="100%" />
<img src="./assets/5. Admin Interface.png" alt="Proof 5 - Admin Interface" width="100%" />
<img src="./assets/6. Security Logs.png" alt="Proof 6 - Security Logs" width="100%" />

---

## Features (current)

- Login with **username or email**
- Registration with `@student.ruet.ac.bd` format validation
- Google Drive-style dashboard UI
- Upload/download/preview files
- Create/open/rename/delete folders
- Rename files
- Trash bin for files and folders (restore, permanent delete, empty trash)
- Share files and folders via:
  - public token links (with expiry)
  - user-to-user share
- Revoke share access (owner-only)
- "Shared with me" supports both files and folders
- File/folder info popup (owner, size, dates, share info)
- Profile page with editable info + avatar upload/remove
- Admin panel for users, files, shares, and logs
- Social share shortcuts (Facebook, WhatsApp, Messenger, Telegram)
- Responsive/mobile-friendly layout

---

## Security currently implemented

- Password hashing with Werkzeug
- Signed Flask session auth
- Session hardening:
  - `SESSION_COOKIE_HTTPONLY=True`
  - `SESSION_COOKIE_SAMESITE='Lax'`
  - `SESSION_COOKIE_SECURE` via env (`1` for HTTPS)
  - 12-hour permanent session lifetime
- Login rate-limit logic for repeated failed attempts
- Restrictive CORS config for `/api/*` with allowlist origins
- Upload filtering:
  - dangerous extension blocking
  - executable magic-byte checks
  - empty file rejection
  - per-user quota enforcement
- Ownership checks for sensitive actions (share/revoke/manage)
- Protected profile image route (user can access only own avatar file)
- SIEM field sanitization before writing logs

---

## SIEM log format (actual)

Logs are written to:

- `logs/access.log`
- `logs/error.log`

Each line follows this structure:

```text
YYYY-MM-DD HH:MM:SS | LEVEL | EVENT=... | IP=... | PATH=... | METHOD=... | UA=... | USERNAME=... | REFERRER=... | CATEGORY=... | OUTCOME=... | STATUS=... | TARGET=... | MESSAGE=...
```

Rotation:

- 10 MB per log file
- 10 backups

---

## Default admin bootstrap

On first run (if no admin exists), app creates:

| Username | Email | Password |
|---|---|---|
| `admin` | `admin@student.ruet.ac.bd` | `admin123` |

Please change the password after first login.

---

## Local run

```bash
git clone https://github.com/InferiorAK/Integrated-Share.git
cd Integrated-Share
pip install -r requirements.txt
python app.py
```

App starts at:

```text
http://<server-ip>:5000
```

---

## Production run (systemd + gunicorn)

Service file in repo: `integrated-share.service`

Gunicorn command:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Manual service setup:

```bash
sudo cp integrated-share.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable integrated-share
sudo systemctl start integrated-share
sudo systemctl status integrated-share
```

One-command installer from GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/InferiorAK/Integrated-Share/main/setup.sh | sudo bash
```

At the end, installer prints:

- start
- stop
- restart
- status
- disable

commands for `integrated-share` service.

---

## Environment variables

- `CORS_ALLOWED_ORIGINS`  
  Default: `http://localhost:5000,http://127.0.0.1:5000`

- `SESSION_COOKIE_SECURE`  
  Set to `1` in HTTPS deployment.

---

## Verified current structure

```text
Integrated-Share/
├── app.py
├── requirements.txt
├── setup.sh
├── integrated-share.service
├── clean.sh
├── core/
│   ├── admin.py
│   ├── auth.py
│   ├── extensions.py
│   ├── files.py
│   ├── logger.py
│   ├── models.py
│   ├── share.py
│   └── utils.py
├── templates/
│   ├── admin.html
│   ├── error.html
│   ├── folder_share.html
│   ├── index.html
│   ├── login.html
│   ├── profile.html
│   └── register.html
├── static/
│   ├── main.js
│   ├── style.css
│   └── images/
├── assets/
│   ├── Banner.jpg
│   ├── Register.png
│   ├── Login.png
│   ├── Sharing Application Interface.png
│   ├── Profile.png
│   ├── Admin Interface.png
│   ├── Security Logs.png
│   ├── Project_Mechanism.png
│   └── Logo.png
├── logs/
├── uploads/
└── instance/
```

