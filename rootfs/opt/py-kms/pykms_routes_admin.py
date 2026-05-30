"""Admin panel routes."""

import datetime

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

import pykms_activation as activation
import pykms_audit as audit
import pykms_auth as auth
import pykms_backup as backup
import pykms_csrf as csrf
import pykms_i18n as i18n
import pykms_ops as ops
from pykms_routes_auth import current_user
from pykms_services import build_stats, delete_client, format_ts, load_clients

admin_bp = Blueprint('admin', __name__)


def _handle_restart_kms():
    name = ops.restart_kms_container()
    activation.clear_pending_restart()
    audit.log('kms_restart', name)
    return i18n.translate('ops.kms_restarted').format(name=name)


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
        elif action == 'restart_kms':
            try:
                success = _handle_restart_kms()
            except Exception as e:
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
        ops_status=ops.ops_status(),
        error=error,
        success=success,
    )


@admin_bp.route('/admin/ops', methods=['GET', 'POST'])
def admin_ops_page():
    error = None
    success = None

    if request.method == 'POST':
        csrf.validate()
        action = request.form.get('action')
        if action == 'restart_kms':
            try:
                success = _handle_restart_kms()
            except Exception as e:
                error = str(e)
        elif action == 'restore_backup':
            upload = request.files.get('backup_file')
            if not upload or not upload.filename:
                error = i18n.translate('ops.restore_missing')
            else:
                try:
                    restored = backup.restore_archive(upload.stream)
                    audit.log('backup_restore', ','.join(restored))
                    success = i18n.translate('ops.restore_ok').format(files=', '.join(restored))
                except Exception as e:
                    error = str(e)

    return render_template(
        'admin_ops.html',
        path='/admin/ops/',
        admin_tab='ops',
        ops_status=ops.ops_status(),
        backup_files=backup.list_backup_files(),
        error=error,
        success=success,
    )


@admin_bp.route('/admin/ops/backup')
def admin_ops_backup_download():
    audit.log('backup_download')
    buf = backup.create_archive()
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    return send_file(
        buf,
        mimetype='application/gzip',
        as_attachment=True,
        download_name=f'kms-gui-backup-{stamp}.tar.gz',
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
        ops_status=ops.ops_status(),
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
