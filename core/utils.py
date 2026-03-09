import os
import math
from functools import wraps

from flask import session, request, redirect, url_for, jsonify

from .extensions import db
from .models import ActivityLog

_SIEM_MAP = {
    'login':             ('AUTH',    'INFO'),
    'login_failure':     ('AUTH',    'MEDIUM'),
    'logout':            ('AUTH',    'INFO'),
    'upload':            ('FILE_OP', 'LOW'),
    'download':          ('FILE_OP', 'LOW'),
    'delete':            ('FILE_OP', 'MEDIUM'),
    'clear_all':         ('FILE_OP', 'HIGH'),
    'share_link':        ('SHARING', 'LOW'),
    'share_user':        ('SHARING', 'LOW'),
    'admin_delete_user': ('ADMIN',   'HIGH'),
    'admin_delete_file': ('ADMIN',   'MEDIUM'),
}


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login_page'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from .models import User
        user = db.session.get(User, session.get('user_id'))
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


def log_action(action, file_name=None, outcome='SUCCESS', username_override=None):
    category, severity = _SIEM_MAP.get(action, ('GENERAL', 'INFO'))
    db.session.add(ActivityLog(
        user_id        = session.get('user_id'),
        username       = username_override or session.get('username'),
        action         = action,
        file_name      = file_name,
        ip_address     = request.remote_addr,
        severity       = severity,
        event_category = category,
        outcome        = outcome,
    ))


def format_file_size(size_bytes):
    if not size_bytes or size_bytes == 0:
        return '0 B'
    k = 1024
    sizes = ['B', 'KB', 'MB', 'GB']
    i = int(math.floor(math.log(size_bytes) / math.log(k)))
    return f"{round(size_bytes / (k ** i), 1)} {sizes[i]}"


BLOCKED_EXTENSIONS = {
    '.php', '.php3', '.php4', '.php5', '.php7', '.php8', '.phtml', '.phar',
    '.asp', '.aspx', '.ascx', '.ashx', '.asmx', '.axd',
    '.jsp', '.jspx', '.jspf',
    '.cgi', '.pl',
    '.htaccess', '.htpasswd',
    '.exe', '.dll', '.com', '.scr', '.pif',
    '.msi', '.msp', '.mst',
    '.bat', '.cmd',
    '.ps1', '.psm1', '.psd1', '.ps2', '.ps2xml', '.psc1', '.psc2',
    '.vbs', '.vbe', '.vbscript',
    '.jse', '.wsf', '.wsh', '.ws',
    '.lnk', '.url',
    '.war',
}

BLOCKED_BINARY_SIGNATURES = [
    b'\x7fELF',
    b'MZ',
    b'\xfe\xed\xfa\xce',
    b'\xfe\xed\xfa\xcf',
    b'\xce\xfa\xed\xfe',
    b'\xcf\xfa\xed\xfe',
    b'\xca\xfe\xba\xbe',
]


def validate_file(filename, file_stream):
    _, ext = os.path.splitext(filename.lower())
    if ext in BLOCKED_EXTENSIONS:
        return False, f"File type '{ext}' is not permitted"

    header = file_stream.read(8)
    file_stream.seek(0)

    if len(header) == 0:
        return False, "Empty file"

    for sig in BLOCKED_BINARY_SIGNATURES:
        if header[:len(sig)] == sig:
            return False, "Executable binary files are not permitted"

    return True, None
