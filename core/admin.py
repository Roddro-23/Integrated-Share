import os
import shutil
from datetime import datetime

from flask import (Blueprint, render_template, session, jsonify,
                   request, redirect, url_for, current_app)

from .extensions import db
from .models import User, SharedFile, FileShare, FolderShare, ActivityLog
from .utils import login_required, admin_required, format_file_size, log_action

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
@login_required
def admin_page():
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_admin:
        return redirect(url_for('files.index'))
    return render_template('admin.html', username=session.get('username'))


@admin_bp.route('/api/admin/stats', methods=['GET'])
@login_required
@admin_required
def admin_stats():
    total_storage = db.session.query(db.func.sum(User.storage_used)).scalar() or 0
    return jsonify({
        'total_users':   User.query.count(),
        'total_files':   SharedFile.query.count(),
        'total_shares':  (FileShare.query.count() + FolderShare.query.count()),
        'total_storage': format_file_size(total_storage),
    })


@admin_bp.route('/api/admin/users', methods=['GET'])
@login_required
@admin_required
def admin_get_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([{
        'id':            u.id,
        'username':      u.username,
        'email':         u.email or '—',
        'is_admin':      u.is_admin,
        'storage_used':  format_file_size(u.storage_used or 0),
        'storage_limit': format_file_size(u.storage_limit or 0),
        'file_count':    len(u.files),
        'created_at':    datetime.fromtimestamp(u.created_at).strftime('%Y-%m-%d %H:%M'),
    } for u in users])


@admin_bp.route('/api/admin/users/<user_id>', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_user(user_id):
    if user_id == session['user_id']:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
    if os.path.exists(user_folder):
        shutil.rmtree(user_folder)
    log_action('admin_delete_user', user.username)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/admin/files', methods=['GET'])
@login_required
@admin_required
def admin_get_files():
    files = SharedFile.query.filter_by(is_deleted=False).order_by(SharedFile.uploaded_at.desc()).all()
    return jsonify([{
        'id':            f.id,
        'original_name': f.original_name,
        'size':          format_file_size(f.size),
        'owner':         f.owner.username if f.owner else '—',
        'uploaded_at':   datetime.fromtimestamp(f.uploaded_at).strftime('%Y-%m-%d %H:%M'),
    } for f in files])


@admin_bp.route('/api/admin/files/<file_id>', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_file(file_id):
    f = db.session.get(SharedFile, file_id)
    if not f:
        return jsonify({'error': 'File not found'}), 404
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f.user_id, f.stored_name)
    if os.path.exists(file_path):
        os.remove(file_path)
    if f.owner:
        f.owner.storage_used = max(0, (f.owner.storage_used or 0) - f.size)
    log_action('admin_delete_file', f.original_name)
    db.session.delete(f)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/admin/logs', methods=['GET'])
@login_required
@admin_required
def admin_get_logs():
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(500).all()
    return jsonify([{
        'timestamp':      datetime.utcfromtimestamp(l.timestamp).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'severity':       l.severity or 'INFO',
        'event_category': l.event_category or 'GENERAL',
        'username':       l.username or '—',
        'action':         l.action,
        'file_name':      l.file_name or '—',
        'ip_address':     l.ip_address or '—',
        'outcome':        l.outcome or 'SUCCESS',
    } for l in logs])


@admin_bp.route('/api/admin/shares', methods=['GET'])
@login_required
@admin_required
def admin_get_shares():
    file_shares = FileShare.query.order_by(FileShare.created_at.desc()).all()
    folder_shares = FolderShare.query.order_by(FolderShare.created_at.desc()).all()
    items = []

    for s in file_shares:
        items.append({
            'id': s.id,
            'type': 'file',
            'target': s.file.original_name if s.file else '—',
            'owner': db.session.get(User, s.shared_by).username if db.session.get(User, s.shared_by) else '—',
            'active': s.is_active,
            'expires_at': datetime.fromtimestamp(s.expires_at).strftime('%Y-%m-%d %H:%M') if s.expires_at else '—',
            'scope': 'public' if not s.shared_with else 'user',
        })
    for s in folder_shares:
        items.append({
            'id': s.id,
            'type': 'folder',
            'target': s.folder.name if s.folder else '—',
            'owner': db.session.get(User, s.shared_by).username if db.session.get(User, s.shared_by) else '—',
            'active': s.is_active,
            'expires_at': datetime.fromtimestamp(s.expires_at).strftime('%Y-%m-%d %H:%M') if s.expires_at else '—',
            'scope': 'public' if not s.shared_with else 'user',
        })
    items.sort(key=lambda x: x['expires_at'], reverse=True)
    return jsonify(items)


@admin_bp.route('/api/admin/shares/<share_type>/<share_id>', methods=['DELETE'])
@login_required
@admin_required
def admin_revoke_share(share_type, share_id):
    if share_type == 'file':
        share = db.session.get(FileShare, share_id)
    elif share_type == 'folder':
        share = db.session.get(FolderShare, share_id)
    else:
        return jsonify({'error': 'Invalid share type'}), 400

    if not share:
        return jsonify({'error': 'Share not found'}), 404
    share.is_active = False
    log_action('admin_delete_file', f'revoke_{share_type}_share')
    db.session.commit()
    return jsonify({'success': True})
