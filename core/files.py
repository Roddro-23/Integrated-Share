import os
import time
import uuid
import shutil
from datetime import datetime

from flask import (Blueprint, render_template, request, session,
                   jsonify, send_file, current_app)
from werkzeug.utils import secure_filename

from .extensions import db
from .models import User, SharedFile, FileShare
from .utils import login_required, log_action, format_file_size, validate_file

files_bp = Blueprint('files', __name__)


@files_bp.route('/')
@login_required
def index():
    return render_template('index.html', username=session.get('username'))


@files_bp.route('/api/files', methods=['GET'])
@login_required
def get_files():
    user_id = session['user_id']

    own_files      = SharedFile.query.filter_by(user_id=user_id).all()
    shared_with_me = FileShare.query.filter_by(shared_with=user_id, is_active=True).all()
    shared_files   = [s.file for s in shared_with_me if s.file]

    seen, all_files = set(), []
    for f in own_files + shared_files:
        if f.id not in seen:
            seen.add(f.id)
            all_files.append(f)
    all_files.sort(key=lambda x: x.uploaded_at, reverse=True)

    return jsonify([{
        'id':             f.id,
        'original_name':  f.original_name,
        'stored_name':    f.stored_name,
        'size':           f.size,
        'size_formatted': format_file_size(f.size),
        'uploaded_at':    f.uploaded_at,
        'date':           datetime.fromtimestamp(f.uploaded_at).strftime('%Y-%m-%d %H:%M'),
        'owner':          f.owner.username if f.user_id != user_id else '',
    } for f in all_files])


@files_bp.route('/api/upload', methods=['POST'])
@login_required
def upload_file():
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    user_id         = session['user_id']
    user            = db.session.get(User, user_id)
    upload_folder   = current_app.config['UPLOAD_FOLDER']
    user_upload_dir = os.path.join(upload_folder, user_id)
    os.makedirs(user_upload_dir, exist_ok=True)

    uploaded, rejected = [], []

    for file in request.files.getlist('files'):
        if not file or not file.filename:
            continue

        allowed, _ = validate_file(file.filename, file.stream)
        if not allowed:
            rejected.append(file.filename)
            continue

        original_name = secure_filename(file.filename)
        base, ext     = os.path.splitext(original_name)
        stored_name   = f"{base}_{str(uuid.uuid4())[:8]}{ext}"
        file_path     = os.path.join(user_upload_dir, stored_name)
        file.save(file_path)
        file_size = os.path.getsize(file_path)

        record = SharedFile(
            id=str(uuid.uuid4()),
            user_id=user_id,
            original_name=original_name,
            stored_name=stored_name,
            size=file_size,
            uploaded_at=time.time(),
        )
        db.session.add(record)
        user.storage_used = (user.storage_used or 0) + file_size
        log_action('upload', original_name)

        uploaded.append({
            'id':             record.id,
            'original_name':  original_name,
            'stored_name':    stored_name,
            'size':           file_size,
            'size_formatted': format_file_size(file_size),
            'uploaded_at':    record.uploaded_at,
            'date':           'just now',
            'owner':          '',
        })

    db.session.commit()

    if not uploaded and rejected:
        return jsonify({
            'error': 'All files were rejected. Executable binaries and server-side scripts are not allowed.'
        }), 400

    response = {'success': True, 'files': uploaded, 'message': f'Uploaded {len(uploaded)} file(s)'}
    if rejected:
        response['warning'] = (
            f'Rejected {len(rejected)} file(s) (executable or server-side script): '
            + ', '.join(rejected)
        )
    return jsonify(response)


@files_bp.route('/api/download/<file_id>')
@login_required
def download_file(file_id):
    user_id   = session['user_id']
    file_info = SharedFile.query.filter_by(stored_name=file_id).first()
    if not file_info:
        return jsonify({'error': 'File not found'}), 404

    owns   = file_info.user_id == user_id
    shared = FileShare.query.filter_by(
        file_id=file_info.id, shared_with=user_id, is_active=True
    ).first()
    if not owns and not shared:
        return jsonify({'error': 'Access denied'}), 403

    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_info.user_id, file_id)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found on server'}), 404

    log_action('download', file_info.original_name)
    db.session.commit()
    return send_file(file_path, as_attachment=True, download_name=file_info.original_name)


@files_bp.route('/api/delete/<file_id>', methods=['DELETE'])
@login_required
def delete_file(file_id):
    user_id   = session['user_id']
    user      = db.session.get(User, user_id)
    file_info = SharedFile.query.filter_by(id=file_id, user_id=user_id).first()
    if not file_info:
        return jsonify({'error': 'File not found'}), 404

    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id, file_info.stored_name)
    if os.path.exists(file_path):
        os.remove(file_path)

    user.storage_used = max(0, (user.storage_used or 0) - file_info.size)
    log_action('delete', file_info.original_name)
    db.session.delete(file_info)
    db.session.commit()
    return jsonify({'success': True, 'message': 'File deleted'})


@files_bp.route('/api/clear', methods=['POST'])
@login_required
def clear_all_files():
    user_id         = session['user_id']
    user            = db.session.get(User, user_id)
    upload_folder   = current_app.config['UPLOAD_FOLDER']
    user_upload_dir = os.path.join(upload_folder, user_id)

    SharedFile.query.filter_by(user_id=user_id).delete()
    user.storage_used = 0
    log_action('clear_all')
    db.session.commit()

    if os.path.exists(user_upload_dir):
        shutil.rmtree(user_upload_dir)
    os.makedirs(user_upload_dir, exist_ok=True)
    return jsonify({'success': True, 'message': 'All files cleared'})
