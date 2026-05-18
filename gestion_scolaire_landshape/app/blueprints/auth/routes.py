# =============================================================
#  EduNova — blueprints/auth/routes.py
#  Login / Logout / Langue
# =============================================================
from flask import render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.blueprints.auth import auth_bp
from app.services.auth_service import authentifier


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user.role)

    error = None
    if request.method == 'POST':
        identifiant = request.form.get('identifiant', '').strip()
        password    = request.form.get('password', '')
        user, msg   = authentifier(identifiant, password)

        if user:
            login_user(user, remember=False)
            session['lang'] = user.preference_langue
            next_page = request.args.get('next')
            return redirect(next_page or _redirect_by_role(user.role))
        else:
            error = msg

    return render_template('auth/login.html', error=error)


@auth_bp.route('/logout')
@login_required
def logout():
    # Marquer hors-ligne
    try:
        from app.extensions import db
        from app.models.communication import StatutConnexion
        sc = StatutConnexion.query.filter_by(utilisateur_id=current_user.id).first()
        if sc:
            sc.est_en_ligne = False
            sc.socket_id    = None
            db.session.commit()
    except Exception:
        pass
    logout_user()
    session.clear()
    flash('Vous avez été déconnecté avec succès.', 'info')
    return redirect(url_for('public.index'))


@auth_bp.route('/langue/<lang>')
def changer_langue(lang):
    """Change la langue de l'interface et met à jour la préférence utilisateur."""
    from app.extensions import db
    if lang in ('ar', 'fr', 'en'):
        session['lang'] = lang
        if current_user.is_authenticated:
            current_user.preference_langue = lang
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
    return redirect(request.referrer or url_for('public.index'))


def _redirect_by_role(role: str) -> str:
    mapping = {
        'admin'      : 'admin.dashboard',
        'professeur' : 'professeur.dashboard',
        'etudiant'   : 'etudiant.dashboard',
        'parent'     : 'parent.dashboard',
    }
    return url_for(mapping.get(role, 'public.index'))
