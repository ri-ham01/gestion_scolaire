# =============================================================
#  EduNova — utils/validators.py
#  Validateurs de données formulaires
# =============================================================
import re
from datetime import date


def valider_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip())) if email else False


def valider_note(valeur) -> bool:
    """Note valide : None ou float entre 0 et 20."""
    if valeur is None or valeur == '':
        return True
    try:
        n = float(valeur)
        return 0.0 <= n <= 20.0
    except (ValueError, TypeError):
        return False


def valider_date(valeur: str, fmt: str = '%Y-%m-%d') -> date | None:
    """Convertit une chaîne en date ou retourne None."""
    if not valeur:
        return None
    try:
        from datetime import datetime
        return datetime.strptime(valeur, fmt).date()
    except ValueError:
        return None


def valider_extension_fichier(filename: str, extensions_autorisees: set) -> bool:
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in extensions_autorisees


def nettoyer_code(code: str) -> str:
    """Retire les espaces et met en majuscules un code de spécialité."""
    return re.sub(r'\s+', '', code or '').upper()


def valider_username(username: str) -> bool:
    """Username : alphanumérique, sans espaces, 3-50 caractères."""
    if not username:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_\-]{3,50}$', username.strip()))


def valider_coefficient(coeff) -> bool:
    try:
        c = int(coeff)
        return 1 <= c <= 10
    except (ValueError, TypeError):
        return False
