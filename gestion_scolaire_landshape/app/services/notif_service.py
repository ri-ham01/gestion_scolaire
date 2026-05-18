# =============================================================
#  EduNova — services/notif_service.py
#  Création de notifications internes et push
# =============================================================
from datetime import datetime, timezone
from app.extensions import db


def envoyer_notification(destinataire_id: int, destinataire_role: str,
                          type_notif: str, titre: str, contenu: str,
                          ref_table: str = None, ref_id: int = None) -> None:
    """Crée une notification en BDD et planifie un push externe."""
    from app.models.communication import Notification, FileNotificationExterne

    notif = Notification(
        type              = type_notif,
        destinataire_id   = destinataire_id,
        destinataire_role = destinataire_role,
        titre             = titre,
        contenu           = contenu,
        reference_table   = ref_table,
        reference_id      = ref_id,
    )
    db.session.add(notif)

    # Planifier la notification push externe (traitée par un worker en fond)
    push = FileNotificationExterne(
        utilisateur_id = destinataire_id,
        canal          = 'push',
        titre          = titre,
        corps          = contenu,
        declencheur    = type_notif,
        reference_table = ref_table,
        reference_id   = ref_id,
    )
    db.session.add(push)

    try:
        db.session.commit()
        # Émettre via SocketIO si l'utilisateur est en ligne
        _emit_socket(destinataire_id, notif)
    except Exception:
        db.session.rollback()


def _emit_socket(utilisateur_id: int, notif) -> None:
    """Émet une notification temps réel via SocketIO."""
    try:
        from app.extensions import socketio
        from app.models.communication import StatutConnexion
        sc = StatutConnexion.query.filter_by(utilisateur_id=utilisateur_id, est_en_ligne=True).first()
        if sc and sc.socket_id:
            socketio.emit('nouvelle_notification', {
                'id'     : notif.id,
                'type'   : notif.type,
                'titre'  : notif.titre,
                'contenu': notif.contenu,
                'date'   : notif.date_envoi.isoformat(),
            }, room=sc.socket_id)
    except Exception:
        pass


def notifier_absence(etudiant_id: int, seance_id: int) -> None:
    """Notifie le parent et l'étudiant d'une absence enregistrée."""
    from app.models.profiles import Etudiant, ParentEtudiant

    etu = db.session.get(Etudiant, etudiant_id)
    if not etu:
        return

    envoyer_notification(
        destinataire_id   = etu.utilisateur_id,
        destinataire_role = 'etudiant',
        type_notif        = 'absence_enregistree',
        titre             = 'Absence enregistrée',
        contenu           = 'Une absence a été enregistrée pour vous.',
        ref_table         = 'presences',
        ref_id            = seance_id,
    )
    for link in ParentEtudiant.query.filter_by(
            etudiant_id=etudiant_id, peut_recevoir_notifications=True).all():
        envoyer_notification(
            destinataire_id   = link.parent.utilisateur_id,
            destinataire_role = 'parent',
            type_notif        = 'absence_enregistree',
            titre             = f'Absence de {etu.nom_complet}',
            contenu           = f'{etu.nom_complet} a été marqué(e) absent(e).',
            ref_table         = 'presences',
            ref_id            = seance_id,
        )


def notifier_message(conversation_id: int, expediteur_id: int,
                      destinataire_id: int, destinataire_role: str) -> None:
    envoyer_notification(
        destinataire_id   = destinataire_id,
        destinataire_role = destinataire_role,
        type_notif        = 'message_recu',
        titre             = 'Nouveau message',
        contenu           = 'Vous avez reçu un nouveau message.',
        ref_table         = 'conversations',
        ref_id            = conversation_id,
    )


def notifier_note_publiee(etudiant_id: int, matiere_nom: str) -> None:
    from app.models.profiles import Etudiant
    etu = db.session.get(Etudiant, etudiant_id)
    if not etu:
        return
    envoyer_notification(
        destinataire_id   = etu.utilisateur_id,
        destinataire_role = 'etudiant',
        type_notif        = 'note_publiee',
        titre             = 'Note disponible',
        contenu           = f'Une note a été saisie pour la matière {matiere_nom}.',
    )
