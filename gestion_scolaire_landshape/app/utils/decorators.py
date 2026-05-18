# =============================================================
#  EduNova — utils/decorators.py
#  Décorateurs de contrôle d'accès par rôle
# =============================================================
from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user


def role_requis(*roles):
    """
    Vérifie que l'utilisateur connecté possède l'un des rôles spécifiés.
    Usage : @role_requis('admin', 'professeur')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                abort(403)
            if not current_user.is_active:
                flash('Votre compte a été désactivé.', 'danger')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_requis(f):
    """Raccourci : accès réservé aux administrateurs."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated


def professeur_requis(f):
    """Raccourci : accès réservé aux professeurs."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'professeur':
            abort(403)
        return f(*args, **kwargs)
    return decorated


def etudiant_requis(f):
    """Raccourci : accès réservé aux étudiants."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'etudiant':
            abort(403)
        return f(*args, **kwargs)
    return decorated


def parent_requis(f):
    """Raccourci : accès réservé aux parents."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'parent':
            abort(403)
        return f(*args, **kwargs)
    return decorated


def compte_actif_requis(f):
    """Vérifie que le compte est actif (non bloqué)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_authenticated and not current_user.is_active:
            from flask import session
            session.clear()
            flash('Votre compte a été désactivé par l\'administration.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def journal_admin_action(action: str, table: str = None):
    """
    Décorateur qui enregistre l'action dans journal_admin.
    Usage : @journal_admin_action('CREATE_ETUDIANT', 'etudiants')
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            result = f(*args, **kwargs)
            if current_user.is_authenticated and current_user.role == 'admin':
                try:
                    from flask import request
                    from app.extensions import db
                    from app.models.audit import JournalAdmin
                    log = JournalAdmin(
                        admin_id      = current_user.administrateur.id,
                        action        = action,
                        table_affectee = table,
                        adresse_ip    = request.remote_addr,
                    )
                    db.session.add(log)
                    db.session.commit()
                except Exception:
                    pass   # Ne pas bloquer si le journal échoue
            return result
        return decorated
    return decorator
