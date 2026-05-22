import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:

    # ── Security ─────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'EduNova2026$SecretKey!XyZ#9f3mK8pQ2rL7vN')

    # ── Database filess.io (MySQL) ───────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', (
        'mysql+pymysql://'
        'gestion_scolaire_landshape'
        ':a635b506c2c42970e3c7b09d88e3e7d657fca2d2'
        '@b7z9qy.h.filess.io'
        ':61001'
        '/gestion_scolaire_landshape'
    ))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # filess.io allows max 5 simultaneous connections
    # Strict pooling to ensure we never open more than 3 connections
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 1,
        'max_overflow': 2,
        'pool_recycle': 280,
        'pool_timeout': 30,
        'pool_pre_ping': True,
        'connect_args': {
            'connect_timeout': 60
        }
    }

    # ── Flask-Babel (i18n) ───────────────────────────────────
    BABEL_DEFAULT_LOCALE    = 'fr'
    BABEL_DEFAULT_TIMEZONE  = 'Africa/Algiers'
    BABEL_SUPPORTED_LOCALES = ['ar', 'fr', 'en']
    LANGUAGES = {
        'ar': 'العربية',
        'fr': 'Français',
        'en': 'English',
    }

    # ── Mail ────────────────────────────────────────────────
    MAIL_SERVER         = os.environ.get('MAIL_SERVER',   None)
    MAIL_PORT           = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS        = os.environ.get('MAIL_USE_TLS',  'false').lower() == 'true'
    MAIL_USERNAME       = os.environ.get('MAIL_USERNAME', None)
    MAIL_PASSWORD       = os.environ.get('MAIL_PASSWORD', None)
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@edunova.dz')

    # ── Upload fichiers ──────────────────────────────────────
    UPLOAD_FOLDER      = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 52_428_800  # 50 MB

    UPLOAD_SUBFOLDERS = ['cours', 'devoirs', 'soumissions',
                         'corrections', 'justifications', 'releves', 'logos']

    ALLOWED_EXTENSIONS = {
        'document': {'pdf', 'doc', 'docx'},
        'image':    {'jpg', 'jpeg', 'png', 'gif', 'webp'},
        'media':    set(),
        'all':      {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'webp'},
    }

    # ── Paramètres pédagogiques par défaut ──────────────────
    SEUIL_PASSAGE       = 10.00
    SEUIL_EXCLUSION_ABS = 10
    DELAI_JUSTIF_HEURES = 48


class DevelopmentConfig(Config):
    DEBUG   = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG   = False
    TESTING = False


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}