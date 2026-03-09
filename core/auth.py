import os
import time
import uuid

from flask import (Blueprint, render_template, request, session,
                   redirect, url_for, jsonify, current_app)

from .extensions import db
from .models import User
from .utils import login_required, log_action

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    if 'user_id' in session:
        return redirect(url_for('files.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('login.html', error='Username and password are required')

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            log_action('login_failure', outcome='FAILURE', username_override=username)
            db.session.commit()
            return render_template('login.html', error='Invalid username or password')

        session.permanent   = True
        session['user_id']  = user.id
        session['username'] = user.username
        log_action('login')
        db.session.commit()
        return redirect(url_for('files.index'))

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register_page():
    if 'user_id' in session:
        return redirect(url_for('files.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        if not username or not email or not password or not confirm:
            return render_template('register.html', error='All fields are required')

        if len(username) < 3 or len(username) > 32:
            return render_template('register.html', error='Username must be 3-32 characters')

        if not username.replace('_', '').replace('-', '').isalnum():
            return render_template('register.html',
                                   error='Username may only contain letters, numbers, hyphens, and underscores')

        local_part, _, domain = email.partition('@')
        if not local_part or domain != 'student.ruet.ac.bd':
            return render_template('register.html',
                                   error='Only RUET student emails are allowed (yourname@student.ruet.ac.bd)')
        if not local_part.replace('.', '').replace('-', '').replace('_', '').isalnum():
            return render_template('register.html', error='Invalid email address')

        if len(password) < 6:
            return render_template('register.html', error='Password must be at least 6 characters')

        if password != confirm:
            return render_template('register.html', error='Passwords do not match')

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already taken')

        if User.query.filter_by(email=email).first():
            return render_template('register.html',
                                   error='An account with this email already exists')

        user = User(id=str(uuid.uuid4()), username=username, email=email, created_at=time.time())
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(os.path.join(upload_folder, user.id), exist_ok=True)
        return redirect(url_for('auth.login_page'))

    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    if 'user_id' in session:
        log_action('logout')
        db.session.commit()
    session.clear()
    return redirect(url_for('auth.login_page'))


@auth_bp.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout():
    log_action('logout')
    db.session.commit()
    session.clear()
    return jsonify({'success': True})


@auth_bp.route('/api/auth/me', methods=['GET'])
@login_required
def api_me():
    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'id':            user.id,
        'username':      user.username,
        'email':         user.email,
        'is_admin':      user.is_admin,
        'storage_limit': user.storage_limit,
        'storage_used':  user.storage_used or 0,
    })
