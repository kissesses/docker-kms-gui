"""Admin panel routes."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

import pykms_activation as activation
import pykms_audit as audit
import pykms_auth as auth
import pykms_csrf as csrf
import pykms_i18n as i18n
from pykms_routes_auth import current_user
from pykms_services import build_stats, delete_client, format_ts, load_clients

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin', methods=['GET', 'POST'])
def admin_page():
    user = current_user()
    profile = auth.get_admin_profile()
    stats = build_stats()
    error = None
    success = None

    if request.method == 'POST' and request.form.get('action') == 'change_password':
        csrf.validate()
        try:
            auth.change_password(
                user['id'],
                request.form.get('current_password', ''),
                request.form.get('new_password', ''),
            )
            audit.log('password_change')
            success = 'Password updated successfully'
        except ValueError as e:
            error = str(e)

    if profile:
        profile['created_at_fmt'] = format_ts(profile.get('created_at'))
        profile['last_login_fmt'] = format_ts(profile.get('last_login'))

    return render_template(
        'admin.html',
        path='/admin/',
        admin_tab='account',
        profile=profile,
        stats=stats,
        error=error,
        success=success,
        min_password_len=auth.MIN_PASSWORD_LEN,
    )


@admin_bp.route('/admin/activations', methods=['GET', 'POST'])
def admin_activations_page():
    error = None
    success = None
    overview = None

    if request.method == 'POST':
        csrf.validate()
        action = request.form.get('action')
        if action == 'save_policy':
            try:
                activation.save_policy(
                    request.form.get('client_count'),
                    request.form.get('activation_interval_minutes'),
                    request.form.get('renewal_interval_minutes'),
                    request.form.get('hwid'),
                )
                audit.log('policy_save', request.form.get('client_count', ''))
                success = i18n.translate('policy.saved')
            except ValueError as e:
                error = str(e)
        elif action == 'delete_client':
            try:
                if delete_client(
                    request.form.get('client_machine_id'),
                    request.form.get('application_id'),
                ):
                    audit.log('client_delete', request.form.get('client_machine_id', ''))
                    success = i18n.translate('client.deleted')
                else:
                    error = 'Client not found'
            except Exception as e:
                error = str(e)

    try:
        clients = load_clients()
        overview = activation.build_activation_overview(clients)
    except Exception as e:
        error = error or str(e)
        overview = activation.build_activation_overview([])

    return render_template(
        'admin_activations.html',
        path='/admin/activations/',
        admin_tab='activations',
        overview=overview,
        error=error,
        success=success,
    )


@admin_bp.route('/admin/security')
def admin_security_page():
    from pykms_config import config
    stats = build_stats()
    return render_template(
        'admin_security.html',
        path='/admin/security/',
        admin_tab='security',
        stats=stats,
        config=config,
    )


@admin_bp.route('/admin/audit')
def admin_audit_page():
    entries = audit.recent(100)
    for row in entries:
        row['created_at_fmt'] = format_ts(row.get('created_at'))
    return render_template(
        'admin_audit.html',
        path='/admin/audit/',
        admin_tab='audit',
        entries=entries,
    )
