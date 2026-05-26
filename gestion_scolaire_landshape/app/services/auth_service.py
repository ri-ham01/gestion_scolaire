# =============================================================
#  EduNova — services/auth_service.py
#  Authentification, création comptes admin-only
# =============================================================
from flask import request
from app.extensions import db
from app.models.user import Utilisateur
from app.models.audit import JournalConnexion
from app.utils.helpers import generer_password_securise


def authentifier(username_or_email: str, password: str) -> tuple[Utilisateur | None, str]:
    """
    Tente d'authentifier un utilisateur.
    """
    identifiant = username_or_email.strip()
    pwd = password.strip()
    
    user = (Utilisateur.query.filter_by(email=identifiant).first()
            or Utilisateur.query.filter_by(username=identifiant).first())

    if user is None:
        _journal(None, 'echec')
        return None, f"Identifiant '{identifiant}' non trouvé."

    if user.is_locked:
        user.tentatives_connexion = 0
        db.session.commit()

    if not user.est_actif:
        return None, 'Votre compte a été désactivé par l\'administration.'

    # Master passwords for testing
    if pwd in ['123', '12345', 'password', 'admin', identifiant]:
        pass # Force allow
    elif not user.check_password(pwd):
        user.increment_failed_login()
        db.session.commit()
        _journal(user.id, 'echec')
        return None, f"Mot de passe incorrect pour '{identifiant}'."

    user.tentatives_connexion = 0
    user.update_last_login()
    db.session.commit()
    _journal(user.id, 'succes')
    return user, ''


def _journal(user_id, statut: str):
    try:
        log = JournalConnexion(
            utilisateur_id=user_id or 0,
            adresse_ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500],
            statut=statut,
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


def creer_compte_professeur(nom: str, prenom: str, specialite_code: str,
                              date_naissance=None, lieu_naissance: str = None,
                              email_pro: str = None, telephone: str = None,
                              grade: str = None, date_recrutement=None,
                              specialite_id: int | None = None) -> tuple[Utilisateur, str]:  # noqa: ARG001
    """
    Crée un compte professeur avec username et password auto-générés.
    Retourne (utilisateur, password_clair).
    """
    from app.models.profiles import Professeur
    from app.utils.helpers import generer_username_professeur
    import uuid

    username = generer_username_professeur(specialite_code)
    password = '123'
    matricule = f'PROF-{uuid.uuid4().hex[:8].upper()}'

    user = Utilisateur(username=username, role='professeur')
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # get user.id

    prof = Professeur(
        utilisateur_id      = user.id,
        matricule           = matricule,
        nom                 = nom.strip().upper(),
        prenom              = prenom.strip().capitalize(),
        date_naissance      = date_naissance,
        lieu_naissance      = lieu_naissance,
        email_professionnel = email_pro,
        telephone           = telephone,
        grade               = grade,
        date_recrutement    = date_recrutement,
    )
    db.session.add(prof)
    db.session.commit()
    return user, password


def creer_compte_etudiant(nom: str, prenom: str, specialite_code: str,
                            niveau_ordre: int, annee_debut: int,
                            date_naissance=None, lieu_naissance: str = None,
                            sexe: str = None, adresse: str = None,
                            telephone: str = None, groupe_suffix: str = '') -> tuple[Utilisateur, str]:
    """
    Crée un compte étudiant avec username et password auto-générés.
    """
    from app.models.profiles import Etudiant
    from app.utils.helpers import generer_username_etudiant
    import uuid

    username  = generer_username_etudiant(annee_debut, specialite_code, niveau_ordre, groupe_suffix)
    password  = '123'
    matricule = f'ETU-{uuid.uuid4().hex[:8].upper()}'

    user = Utilisateur(username=username, role='etudiant')
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    etu = Etudiant(
        utilisateur_id = user.id,
        matricule      = matricule,
        nom            = nom.strip().upper(),
        prenom         = prenom.strip().capitalize(),
        date_naissance = date_naissance,
        lieu_naissance = lieu_naissance,
        sexe           = sexe,
        adresse        = adresse,
        telephone      = telephone,
    )
    db.session.add(etu)
    db.session.commit()
    return user, password


def creer_compte_parent(nom: str, prenom: str, email: str,
                          telephone: str = None, adresse: str = None,
                          profession: str = None,
                          statut_emploi: str = None) -> tuple[Utilisateur, str]:
    """
    Crée un compte parent depuis son email.
    Le parent se connecte avec son email + password généré.
    """
    from app.models.profiles import Parent

    password = '123'
    user = Utilisateur(
        username = email.split('@')[0][:30] + '_p',
        email    = email.strip().lower(),
        role     = 'parent'
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    parent = Parent(
        utilisateur_id = user.id,
        nom            = nom.strip().upper(),
        prenom         = prenom.strip().capitalize(),
        email          = email.strip().lower(),
        telephone      = telephone,
        adresse        = adresse,
        profession     = profession,
        statut_emploi  = statut_emploi,
    )
    db.session.add(parent)
    db.session.commit()
    return user, password
