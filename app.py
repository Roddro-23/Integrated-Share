import os
import time
import uuid

from flask import Flask
from flask_cors import CORS

from core.extensions import db
from core.models import User, SharedFile, FileShare, ActivityLog
from core.auth  import auth_bp
from core.files import files_bp
from core.share import share_bp
from core.admin import admin_bp

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER   = 'uploads'
SECRET_KEY_FILE = '.secret_key'

app.config['UPLOAD_FOLDER']                  = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH']             = 500 * 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///integrated_share.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, 'rb') as _f:
        app.secret_key = _f.read()
else:
    _key = os.urandom(32)
    with open(SECRET_KEY_FILE, 'wb') as _f:
        _f.write(_key)
    app.secret_key = _key

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
            email      = None,
            is_admin   = True,
            created_at = time.time(),
        )
        admin.set_password('$admin_tjrs$')
        db.session.add(admin)
        db.session.commit()
        print("Default admin created - username: admin  password: $admin_tjrs$")
        print("Change the admin password after first login.")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
