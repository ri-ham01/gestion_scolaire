import os
from flask import Flask, session, request, g
from flask_babel import Babel
from app.extensions import db, migrate, bcrypt, socketio, mail, login_manager, babel


def create_app(config_name='default'):
    from config import config

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # ── Babel locale selector ──────────────────────────────────
    def get_locale():
        # Priority: session lang → browser accept → default fr
        lang = session.get('lang', None)
        if lang in ('ar', 'fr', 'en'):
            return lang
        return request.accept_languages.best_match(['ar', 'fr', 'en'], default='fr')

    # ── Init extensions ────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    socketio.init_app(app, cors_allowed_origins='*', async_mode='threading')

    # ── Register Blueprints ────────────────────────────────────
    from app.blueprints.auth.routes    import auth_bp
    from app.blueprints.public.routes  import public_bp
    from app.blueprints.admin.routes   import admin_bp
    from app.blueprints.professeur.routes import prof_bp
    from app.blueprints.etudiant.routes   import etudiant_bp
    from app.blueprints.parent.routes     import parent_bp
    from app.blueprints.api.routes        import api_bp

    app.register_blueprint(auth_bp,      url_prefix='/auth')
    app.register_blueprint(public_bp,    url_prefix='/')
    app.register_blueprint(admin_bp,     url_prefix='/admin')
    app.register_blueprint(prof_bp,      url_prefix='/professeur')
    app.register_blueprint(etudiant_bp,  url_prefix='/etudiant')
    app.register_blueprint(parent_bp,    url_prefix='/parent')
    app.register_blueprint(api_bp,       url_prefix='/api')

    # ── Register socket events ─────────────────────────────────
    from app.sockets import chat  # noqa: F401

    # ── Shell context ──────────────────────────────────────────
    @app.shell_context_processor
    def make_shell_context():
        return dict(db=db, app=app)

    return app