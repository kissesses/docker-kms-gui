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
        'health.healthy': 'Within renewal window',
        'health.due_soon': 'Renewal check expected soon',
        'health.overdue': 'Past expected renewal interval',
        'health.grace': 'Grace period — activation pending',
        'health.at_risk': 'Extended grace — client may deactivate',
        'health.unknown': 'Unknown status',
        'policy.saved': 'Policy saved. Restart KMS container to apply: docker compose restart kms',
        'client.deleted': 'Client removed from database',
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
        'health.healthy': 'В окне продления',
        'health.due_soon': 'Скоро проверка продления',
        'health.overdue': 'Просрочено продление',
        'health.grace': 'Grace period — ожидает активации',
        'health.at_risk': 'Риск деактивации',
        'health.unknown': 'Неизвестно',
        'policy.saved': 'Политика сохранена. Перезапустите KMS: docker compose restart kms',
        'client.deleted': 'Клиент удалён из базы',
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
