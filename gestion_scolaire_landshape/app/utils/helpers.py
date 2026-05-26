# =============================================================
#  EduNova — utils/helpers.py
#  Fonctions utilitaires globales
# =============================================================
import os
import re
import uuid
import secrets
import string
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import current_app


# ─────────────────────────────────────────────────────────────
#  PARAMÈTRES SYSTÈME
# ─────────────────────────────────────────────────────────────

def get_param(cle: str, defaut: str = '') -> str:
    """Lit un paramètre depuis la table parametres_systeme."""
    from app.extensions import db
    try:
        from sqlalchemy import text
        row = db.session.execute(
            text("SELECT valeur FROM parametres_systeme WHERE cle = :cle"),
            {'cle': cle}
        ).fetchone()
        return row[0] if row else defaut
    except Exception:
        return defaut


def get_param_float(cle: str, defaut: float = 0.0) -> float:
    try:
        return float(get_param(cle, str(defaut)))
    except (ValueError, TypeError):
        return defaut


def get_param_int(cle: str, defaut: int = 0) -> int:
    try:
        return int(get_param(cle, str(defaut)))
    except (ValueError, TypeError):
        return defaut


# ─────────────────────────────────────────────────────────────
#  GÉNÉRATION AUTOMATIQUE DE USERNAMES
# ─────────────────────────────────────────────────────────────

def generer_username_professeur(specialite_code: str) -> str:
    """
    Format : prof_<code_spe><NNN> → ex: prof_math1, prof_math2
    Cherche le max existant pour ce préfixe et incrémente.
    """
    from app.models.user import Utilisateur
    from app.extensions import db
    prefix = f"prof_{specialite_code.lower().strip()}"
    # Trouver le dernier numéro pour ce préfixe
    pattern = f'{prefix}%'
    existing = db.session.query(Utilisateur).filter(
        Utilisateur.role == 'professeur',
        Utilisateur.username.like(pattern)
    ).all()
    max_num = 0
    for u in existing:
        m = re.match(rf'^{re.escape(prefix)}(\d+)$', u.username)
        if m:
            max_num = max(max_num, int(m.group(1)))
    num = max_num + 1
    return f'{prefix}{num}'


def generer_username_etudiant(annee_scolaire_debut: int,
                               specialite_code: str,
                               niveau_ordre: int,
                               groupe_suffix: str = '') -> str:
    """
    Format : <YY><code_spe><groupe_suffix>_<NN> → ex: 26mathA_1, 26infoA_5
    YY = 2 derniers chiffres de l'année de début.
    """
    from app.models.user import Utilisateur
    from app.extensions import db
    yy     = str(annee_scolaire_debut)[-2:]
    prefix = f'{yy}{specialite_code.lower()}{groupe_suffix}'
    pattern = f'{prefix}%'
    existing = db.session.query(Utilisateur).filter(
        Utilisateur.role == 'etudiant',
        Utilisateur.username.like(pattern)
    ).all()
    max_num = 0
    for u in existing:
        m = re.match(rf'^{re.escape(prefix)}_(\d+)$', u.username)
        if m:
            max_num = max(max_num, int(m.group(1)))
    num = max_num + 1
    return f'{prefix}_{num}'


def generer_password_securise(longueur: int = 12) -> str:
    """Génère un mot de passe aléatoire sécurisé lisible."""
    alphabet = string.ascii_letters + string.digits + '!@#$'
    while True:
        pwd = ''.join(secrets.choice(alphabet) for _ in range(longueur))
        # Au moins 1 majuscule, 1 minuscule, 1 chiffre, 1 spécial
        if (any(c.isupper() for c in pwd)
                and any(c.islower() for c in pwd)
                and any(c.isdigit() for c in pwd)
                and any(c in '!@#$' for c in pwd)):
            return pwd


def generer_token_qr() -> str:
    """UUID4 sans tirets pour les QR codes de relevé."""
    return uuid.uuid4().hex


# ─────────────────────────────────────────────────────────────
#  FICHIERS
# ─────────────────────────────────────────────────────────────

def allowed_file(filename: str, categorie: str = 'all') -> bool:
    allowed = current_app.config['ALLOWED_EXTENSIONS'].get(categorie, set())
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed


def extension_fichier(filename: str) -> str:
    if not filename or '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()


def type_fichier_pedagogique(filename: str) -> str:
    """Type stocké pour devoirs, corrections, soumissions (enum pdf/word/image/autre)."""
    ext = extension_fichier(filename)
    if ext == 'pdf':
        return 'pdf'
    if ext in ('doc', 'docx'):
        return 'word'
    if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return 'image'
    return 'autre'


def type_contenu_cours(filename: str) -> str:
    """Type stocké pour la table cours (enum sans valeur word)."""
    ext = extension_fichier(filename)
    if ext == 'pdf':
        return 'pdf'
    if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
        return 'image'
    if ext in ('doc', 'docx'):
        return 'lien_externe'
    return 'lien_externe'


def chemin_absolu_upload(fichier_url_rel: str) -> str | None:
    """Construit le chemin absolu à partir d'une URL relative (uploads/...)."""
    if not fichier_url_rel:
        return None
    parts = fichier_url_rel.replace('\\', '/').split('/')
    if not parts or parts[0] != 'uploads':
        return None
    return os.path.join(current_app.config['UPLOAD_FOLDER'], *parts[1:])


def sauvegarder_fichier(file_obj, sous_dossier: str, prefix: str = '') -> str | None:
    """
    Sauvegarde un fichier uploadé et retourne le chemin relatif
    depuis le dossier static (pour stockage en BDD).
    Retourne None si le fichier n'est pas valide.
    """
    if not file_obj or file_obj.filename == '':
        return None
    if not allowed_file(file_obj.filename, 'all'):
        return None
    original_ext = extension_fichier(file_obj.filename) or 'bin'
    filename  = secure_filename(file_obj.filename)
    if not filename:
        filename = f"fichier.{original_ext}"
    unique    = f'{prefix}_{uuid.uuid4().hex[:8]}.{original_ext}' if prefix else f'{uuid.uuid4().hex}.{original_ext}'
    dossier   = os.path.join(current_app.config['UPLOAD_FOLDER'], sous_dossier)
    os.makedirs(dossier, exist_ok=True)
    chemin    = os.path.join(dossier, unique)
    file_obj.save(chemin)
    # Chemin relatif pour URL Flask
    return f'uploads/{sous_dossier}/{unique}'


def taille_ko(chemin_absolu: str) -> int:
    """Retourne la taille en Ko d'un fichier."""
    try:
        return os.path.getsize(chemin_absolu) // 1024
    except OSError:
        return 0


# ─────────────────────────────────────────────────────────────
#  DATES & DIVERS
# ─────────────────────────────────────────────────────────────

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def format_date(d, fmt: str = '%d/%m/%Y') -> str:
    if d is None:
        return '—'
    if isinstance(d, str):
        return d
    return d.strftime(fmt)


def mention_from_moyenne(moy: float | None) -> str:
    if moy is None:
        return '—'
    if moy >= 16: return 'Très Bien'
    if moy >= 14: return 'Bien'
    if moy >= 12: return 'Assez Bien'
    if moy >= 10: return 'Passable'
    return 'Insuffisant'


def paginate_query(query, page: int, per_page: int = 20):
    """Wrapper pratique pour la pagination SQLAlchemy."""
    return query.paginate(page=page, per_page=per_page, error_out=False)
