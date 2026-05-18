# =============================================================
#  EduNova — services/mail_service.py
#  Envoi d'emails via Flask-Mail
# =============================================================
from flask import current_app
from flask_mail import Message as MailMessage


def envoyer_email(destinataire: str, sujet: str, corps_html: str,
                  corps_texte: str = None) -> bool:
    """
    Envoie un email via Flask-Mail.
    Retourne True si succès, False sinon.
    """
    try:
        from app.extensions import mail
        msg = MailMessage(
            subject    = sujet,
            recipients = [destinataire],
            html       = corps_html,
            body       = corps_texte or _strip_html(corps_html),
            sender     = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@edunova.dz'),
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f'[MailService] Erreur envoi email à {destinataire}: {e}')
        return False


def envoyer_mot_de_passe(destinataire_email: str, nom_complet: str,
                          username: str, password: str) -> bool:
    """Envoie les identifiants de connexion à un utilisateur."""
    sujet = 'Vos identifiants EduNova'
    html  = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
        <div style="background:#4F46E5;padding:24px;border-radius:12px 12px 0 0">
            <h1 style="color:#fff;margin:0;font-size:24px">EduNova</h1>
            <p style="color:#c7d2fe;margin:4px 0 0">Bienvenue sur votre espace numérique</p>
        </div>
        <div style="background:#0f172a;padding:32px;border-radius:0 0 12px 12px">
            <p style="color:#e2e8f0">Bonjour <strong style="color:#fff">{nom_complet}</strong>,</p>
            <p style="color:#94a3b8">Votre compte a été créé. Voici vos identifiants de connexion :</p>
            <div style="background:#1e293b;border-radius:8px;padding:16px;margin:16px 0">
                <p style="color:#94a3b8;margin:0 0 8px"><strong style="color:#06B6D4">Identifiant :</strong></p>
                <code style="color:#fff;font-size:18px;letter-spacing:2px">{username}</code>
                <p style="color:#94a3b8;margin:16px 0 8px"><strong style="color:#06B6D4">Mot de passe :</strong></p>
                <code style="color:#fff;font-size:18px;letter-spacing:2px">{password}</code>
            </div>
            <p style="color:#ef4444;font-size:13px">⚠️ Conservez ces informations en lieu sûr. Ne partagez jamais votre mot de passe.</p>
            <div style="text-align:center;margin-top:24px">
                <a href="#" style="background:#4F46E5;color:#fff;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:600">
                    Se connecter
                </a>
            </div>
        </div>
        <p style="color:#475569;text-align:center;font-size:12px;margin-top:16px">
            © 2026 EduNova — Système de Gestion Scolaire
        </p>
    </div>
    """
    return envoyer_email(destinataire_email, sujet, html)


def envoyer_notification_absence(parent_email: str, parent_nom: str,
                                  etudiant_nom: str, matiere: str,
                                  date_seance: str) -> bool:
    """Notifie un parent par email d'une absence de son enfant."""
    sujet = f'Absence signalée — {etudiant_nom}'
    html  = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
        <div style="background:#EF4444;padding:20px;border-radius:12px 12px 0 0">
            <h2 style="color:#fff;margin:0">⚠️ Absence signalée</h2>
        </div>
        <div style="background:#0f172a;padding:24px;border-radius:0 0 12px 12px">
            <p style="color:#e2e8f0">Bonjour <strong style="color:#fff">{parent_nom}</strong>,</p>
            <p style="color:#94a3b8">
                Une absence a été enregistrée pour votre enfant
                <strong style="color:#fff">{etudiant_nom}</strong>
                lors du cours de <strong style="color:#06B6D4">{matiere}</strong>
                le <strong style="color:#fff">{date_seance}</strong>.
            </p>
            <p style="color:#94a3b8">
                Si vous connaissez la raison de cette absence, vous pouvez la justifier
                en vous connectant à votre espace parent.
            </p>
        </div>
    </div>
    """
    return envoyer_email(parent_email, sujet, html)


def _strip_html(html: str) -> str:
    """Supprime les balises HTML pour la version texte."""
    import re
    return re.sub(r'<[^>]+>', '', html).strip()
