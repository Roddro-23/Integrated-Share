import os
import time
import uuid
from datetime import timedelta

from flask import Flask
from flask_cors import CORS

from core.extensions import db
from core.models import User, SharedFile, FileShare, ActivityLog, Folder, FolderShare
from core.logger import setup_logging, register_request_logging, log_siem_event
from core.auth  import auth_bp
from core.files import files_bp
from core.share import share_bp
from core.admin import admin_bp

app = Flask(__name__)
_allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:5000,http://127.0.0.1:5000'
    ).split(',')
    if origin.strip()
]
CORS(
    app,
    resources={r"/api/*": {"origins": _allowed_origins}},
    supports_credentials=True,
    methods=['GET', 'POST', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'X-Requested-With'],
)

UPLOAD_FOLDER   = 'uploads'
LOG_FOLDER      = 'logs'
SECRET_KEY_FILE = '.secret_key'

app.config['UPLOAD_FOLDER']                  = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH']             = 500 * 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///integrated_share.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_HTTPONLY']        = True
app.config['SESSION_COOKIE_SAMESITE']        = 'Lax'
app.config['SESSION_COOKIE_SECURE']          = os.getenv('SESSION_COOKIE_SECURE', '0') == '1'
app.config['PERMANENT_SESSION_LIFETIME']     = timedelta(hours=12)

if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, 'rb') as _f:
        app.secret_key = _f.read()
else:
    _key = os.urandom(32)
    with open(SECRET_KEY_FILE, 'wb') as _f:
        _f.write(_key)
    app.secret_key = _key

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)
setup_logging(app, LOG_FOLDER)
register_request_logging(app)

db.init_app(app)

app.register_blueprint(auth_bp)
app.register_blueprint(files_bp)
app.register_blueprint(share_bp)
app.register_blueprint(admin_bp)

with app.app_context():
    db.create_all()

    from sqlalchemy import text as _text
    _new_cols = [
        "ALTER TABLE activity_logs ADD COLUMN severity TEXT DEFAULT 'INFO'",
        "ALTER TABLE activity_logs ADD COLUMN event_category TEXT DEFAULT 'GENERAL'",
        "ALTER TABLE activity_logs ADD COLUMN outcome TEXT DEFAULT 'SUCCESS'",
        "ALTER TABLE files ADD COLUMN folder_id TEXT",
        "ALTER TABLE files ADD COLUMN is_deleted BOOLEAN DEFAULT 0",
        "ALTER TABLE files ADD COLUMN deleted_at FLOAT",
        "ALTER TABLE users ADD COLUMN full_name TEXT",
        "ALTER TABLE users ADD COLUMN dob TEXT",
        "ALTER TABLE users ADD COLUMN academic_series TEXT",
        "ALTER TABLE users ADD COLUMN department TEXT",
        "ALTER TABLE users ADD COLUMN profile_image TEXT",
        "ALTER TABLE folder_shares ADD COLUMN shared_with TEXT",
        "ALTER TABLE folders ADD COLUMN is_deleted BOOLEAN DEFAULT 0",
        "ALTER TABLE folders ADD COLUMN deleted_at FLOAT",
    ]
    with db.engine.connect() as _conn:
        for _sql in _new_cols:
            try:
                _conn.execute(_text(_sql))
                _conn.commit()
            except Exception:
                pass

    if not User.query.filter_by(is_admin=True).first():
        admin = User(
            id         = str(uuid.uuid4()),
            username   = 'admin',
            email      = 'admin@student.ruet.ac.bd',
            is_admin   = True,
            created_at = time.time(),
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Default admin created - username: admin  password: admin123")
        print("Change the admin password after first login.")
        log_siem_event(
            action='bootstrap_admin',
            severity='INFO',
            event_category='ADMIN',
            outcome='SUCCESS',
            target='admin',
            message='default admin created',
            username='admin',
            stream='access',
        )

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
