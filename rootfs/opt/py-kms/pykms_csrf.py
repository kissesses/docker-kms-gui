"""CSRF protection for form submissions."""

import secrets

from flask import session, abort


def get_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def validate():
    token = session.get('_csrf_token')
    submitted = None
    from flask import request
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        submitted = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
    if not token or not submitted or submitted != token:
        abort(400, description='Invalid or missing CSRF token')


def inject():
    return {'csrf_token': get_token()}
