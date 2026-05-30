"""Lightweight i18n (English / Russian)."""

from flask import request, session

from pykms_config import config

MESSAGES = {
    'en': {
        'nav.dashboard': 'Dashboard',
        'nav.clients': 'Clients',
        'nav.products': 'Products',
        'nav.license': 'License',
        'nav.admin': 'Admin',
        'nav.export': 'Export',
        'nav.sign_out': 'Sign out',
        'admin.account': 'Account',
        'admin.activations': 'Activations',
        'admin.security': 'Security',
        'admin.audit': 'Audit log',
        'admin.ops': 'Operations',
        'health.healthy': 'Within renewal window',
        'health.due_soon': 'Renewal check expected soon',
        'health.overdue': 'Past expected renewal interval',
        'health.grace': 'Grace period — activation pending',
        'health.at_risk': 'Extended grace — client may deactivate',
        'health.unknown': 'Unknown status',
        'policy.saved': 'Policy saved. Restart the KMS container to apply changes.',
        'policy.pending_restart': 'Policy changed — restart KMS to apply new intervals.',
        'client.deleted': 'Client removed from database',
        'ops.subtitle': 'Backup, restore and KMS container control',
        'ops.kms_title': 'KMS container',
        'ops.kms_desc': 'Restart applies saved policy from kms-policy.json.',
        'ops.restart_kms': 'Restart KMS',
        'ops.restart_confirm': 'Restart the KMS container now?',
        'ops.kms_restarted': 'KMS container restarted: {name}',
        'ops.docker_hint': 'Set OPS_DOCKER_ENABLED=true and mount /var/run/docker.sock to enable restart from the GUI.',
        'ops.backup_title': 'Backup',
        'ops.backup_desc': 'Download databases and policy as a tar.gz archive.',
        'ops.download_backup': 'Download backup',
        'ops.restore_title': 'Restore',
        'ops.restore_file': 'Backup archive (.tar.gz)',
        'ops.restore_submit': 'Restore backup',
        'ops.restore_confirm': 'Replace current data with this backup?',
        'ops.restore_missing': 'Choose a backup file to upload.',
        'ops.restore_ok': 'Restored files: {files}',
        'ops.webhook_title': 'Webhooks',
        'ops.webhook_desc': 'Configure via environment variables and restart the GUI container.',
    },
    'ru': {
        'nav.dashboard': 'Панель',
        'nav.clients': 'Клиенты',
        'nav.products': 'Продукты',
        'nav.license': 'Лицензия',
        'nav.admin': 'Админ',
        'nav.export': 'Экспорт',
        'nav.sign_out': 'Выход',
        'admin.account': 'Аккаунт',
        'admin.activations': 'Активации',
        'admin.security': 'Безопасность',
        'admin.audit': 'Журнал',
        'admin.ops': 'Операции',
        'health.healthy': 'В окне продления',
        'health.due_soon': 'Скоро проверка продления',
        'health.overdue': 'Просрочено продление',
        'health.grace': 'Grace period — ожидает активации',
        'health.at_risk': 'Риск деактивации',
        'health.unknown': 'Неизвестно',
        'policy.saved': 'Политика сохранена. Перезапустите контейнер KMS для применения.',
        'policy.pending_restart': 'Политика изменена — перезапустите KMS для применения интервалов.',
        'client.deleted': 'Клиент удалён из базы',
        'ops.subtitle': 'Резервное копирование и управление контейнером KMS',
        'ops.kms_title': 'Контейнер KMS',
        'ops.kms_desc': 'Перезапуск применяет политику из kms-policy.json.',
        'ops.restart_kms': 'Перезапустить KMS',
        'ops.restart_confirm': 'Перезапустить контейнер KMS сейчас?',
        'ops.kms_restarted': 'Контейнер KMS перезапущен: {name}',
        'ops.docker_hint': 'Укажите OPS_DOCKER_ENABLED=true и смонтируйте /var/run/docker.sock для перезапуска из GUI.',
        'ops.backup_title': 'Резервная копия',
        'ops.backup_desc': 'Скачать базы и policy в архиве tar.gz.',
        'ops.download_backup': 'Скачать backup',
        'ops.restore_title': 'Восстановление',
        'ops.restore_file': 'Архив backup (.tar.gz)',
        'ops.restore_submit': 'Восстановить',
        'ops.restore_confirm': 'Заменить текущие данные этим backup?',
        'ops.restore_missing': 'Выберите файл backup.',
        'ops.restore_ok': 'Восстановлено: {files}',
        'ops.webhook_title': 'Webhooks',
        'ops.webhook_desc': 'Настраивается через переменные окружения и перезапуск GUI.',
    },
}


def get_lang():
    lang = request.cookies.get('lang') or session.get('lang') or config.DEFAULT_LANG
    return lang if lang in MESSAGES else 'en'


def translate(key, lang=None):
    lang = lang or get_lang()
    return MESSAGES.get(lang, MESSAGES['en']).get(key, MESSAGES['en'].get(key, key))


def inject():
    lang = get_lang()
    return {'lang': lang, 't': lambda k: translate(k, lang)}
