"""Authentication routes."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

import pykms_audit as audit
import pykms_auth as auth
import pykms_csrf as csrf

auth_bp = Blueprint('auth', __name__)


def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return auth.get_user_by_id(uid)


@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup_page():
    if not auth.is_enabled():
        return redirect(url_for('pages.dashboard'))
    if auth.is_setup_complete():
        return redirect(url_for('pages.dashboard'))
    error = None
    if request.method == 'POST':
        csrf.validate()
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        if password != confirm:
            error = 'Passwords do not match'
        else:
            try:
                auth.create_admin(username, password)
                user = auth.verify_login(username, password)
                session.clear()
                session.permanent = True
                session['user_id'] = user['id']
                session['username'] = user['username']
                audit.log('setup', f'admin={username}', username=username)
                flash('Administrator account created successfully.', 'success')
                return redirect(url_for('pages.dashboard'))
            except ValueError as e:
                error = str(e)
    return render_template('setup.html', path='/setup/', error=error)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    if not auth.is_enabled():
        return redirect(url_for('pages.dashboard'))
    if not auth.is_setup_complete():
        return redirect(url_for('auth.setup_page'))
    error = None
    nxt = request.args.get('next') or request.form.get('next') or url_for('pages.dashboard')
    if request.method == 'POST':
        csrf.validate()
        user = auth.verify_login(
            request.form.get('username', ''),
            request.form.get('password', ''),
        )
        if user:
            session.clear()
            session.permanent = request.form.get('remember') == 'on'
            session['user_id'] = user['id']
            session['username'] = user['username']
            audit.log('login', username=user['username'])
            if not nxt.startswith('/') or nxt.startswith('//'):
                nxt = url_for('pages.dashboard')
            return redirect(nxt)
        audit.log('login_failed', request.form.get('username', ''))
        error = 'Invalid username or password'
    return render_template('login.html', path='/login/', error=error, next_url=nxt)


@auth_bp.route('/logout', methods=['POST'])
def logout_page():
    csrf.validate()
    audit.log('logout')
    session.clear()
    if auth.is_enabled():
        flash('You have been signed out.', 'success')
        return redirect(url_for('auth.login_page'))
    return redirect(url_for('pages.dashboard'))


@auth_bp.route('/lang/<lang_code>')
def set_lang(lang_code):
    from flask import make_response, redirect
    if lang_code not in ('en', 'ru'):
        lang_code = 'en'
    session['lang'] = lang_code
    resp = make_response(redirect(request.referrer or url_for('pages.dashboard')))
    resp.set_cookie('lang', lang_code, max_age=365 * 86400, samesite='Lax')
    return resp
