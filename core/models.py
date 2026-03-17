import time
import uuid

from .extensions import db


class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username      = db.Column(db.String(32), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=True)
    full_name     = db.Column(db.String(120), nullable=True)
    dob           = db.Column(db.String(20), nullable=True)
    academic_series = db.Column(db.String(40), nullable=True)
    department    = db.Column(db.String(80), nullable=True)
    profile_image = db.Column(db.String(255), nullable=True)
    password_hash = db.Column(db.Text, nullable=False)
    is_admin      = db.Column(db.Boolean, default=False)
    storage_limit = db.Column(db.BigInteger, default=1 * 1024 * 1024 * 1024)
    storage_used  = db.Column(db.BigInteger, default=0)
    created_at    = db.Column(db.Float, nullable=False, default=time.time)
    files         = db.relationship('SharedFile', backref='owner', lazy=True,
                                    cascade='all, delete-orphan')
    folders       = db.relationship('Folder', backref='owner', lazy=True,
                                    cascade='all, delete-orphan')

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)


class Folder(db.Model):
    __tablename__ = 'folders'
    id            = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id       = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    name          = db.Column(db.String(120), nullable=False)
    is_deleted    = db.Column(db.Boolean, default=False)
    deleted_at    = db.Column(db.Float, nullable=True)
    created_at    = db.Column(db.Float, nullable=False, default=time.time)
    shares        = db.relationship('FolderShare', backref='folder', lazy=True,
                                    cascade='all, delete-orphan')


class SharedFile(db.Model):
    __tablename__ = 'files'
    id            = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id       = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    original_name = db.Column(db.Text, nullable=False)
    stored_name   = db.Column(db.Text, nullable=False)
    size          = db.Column(db.BigInteger, nullable=False)
    folder_id     = db.Column(db.String(36), db.ForeignKey('folders.id'), nullable=True)
    is_deleted    = db.Column(db.Boolean, default=False)
    deleted_at    = db.Column(db.Float, nullable=True)
    uploaded_at   = db.Column(db.Float, nullable=False, default=time.time)
    shares        = db.relationship('FileShare', backref='file', lazy=True,
                                    cascade='all, delete-orphan')
    folder        = db.relationship('Folder', backref='files', lazy=True)


class FileShare(db.Model):
    __tablename__ = 'file_shares'
    id          = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id     = db.Column(db.String(36), db.ForeignKey('files.id'), nullable=False)
    shared_by   = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    shared_with = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    share_token = db.Column(db.String(64), unique=True, nullable=False)
    expires_at  = db.Column(db.Float, nullable=True)
    created_at  = db.Column(db.Float, nullable=False, default=time.time)
    is_active   = db.Column(db.Boolean, default=True)


class FolderShare(db.Model):
    __tablename__ = 'folder_shares'
    id          = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    folder_id   = db.Column(db.String(36), db.ForeignKey('folders.id'), nullable=False)
    shared_by   = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    shared_with = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    share_token = db.Column(db.String(64), unique=True, nullable=False)
    expires_at  = db.Column(db.Float, nullable=True)
    created_at  = db.Column(db.Float, nullable=False, default=time.time)
    is_active   = db.Column(db.Boolean, default=True)


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.String(36), nullable=True)
    username       = db.Column(db.String(32), nullable=True)
    action         = db.Column(db.String(50), nullable=False)
    file_name      = db.Column(db.Text, nullable=True)
    ip_address     = db.Column(db.String(45), nullable=True)
    severity       = db.Column(db.String(10), nullable=True, default='INFO')
    event_category = db.Column(db.String(20), nullable=True, default='GENERAL')
    outcome        = db.Column(db.String(10), nullable=True, default='SUCCESS')
    timestamp      = db.Column(db.Float, nullable=False, default=time.time)
