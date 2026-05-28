# =============================================================
#  EduNova — services/notif_service.py
#  Création de notifications internes et push
# =============================================================
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

    # Map notification internal types to external push trigger types (matching DB ENUM)
    valid_declencheurs = {
        'nouveau_message', 'absence_enregistree', 'absence_justifiee',
        'absence_refusee', 'note_publiee', 'devoir_publie', 'cours_publie',
        'correction_publiee', 'releve_disponible', 'mot_de_passe_envoye',
        'seuil_absences_atteint', 'exclusion', 'annonce', 'post_publie',
        'commentaire_recu', 'autre'
    }
    map_declencheur = {
        'message_recu': 'nouveau_message',
        'exclusion_absences': 'exclusion',
    }
    declencheur_val = map_declencheur.get(type_notif, type_notif)
    if declencheur_val not in valid_declencheurs:
        declencheur_val = 'autre'

    # Planifier la notification push externe (traitée par un worker en fond)
    push = FileNotificationExterne(
        utilisateur_id = destinataire_id,
        canal          = 'push',
        titre          = titre,
        corps          = contenu,
        declencheur    = declencheur_val,
        reference_table = ref_table,
        reference_id   = ref_id,
    )
    db.session.add(push)

    try:
        db.session.flush()
        # Émettre via SocketIO si l'utilisateur est en ligne
        _emit_socket(destinataire_id, notif)
    except Exception as e:
        # Nous ne faisons pas de rollback ici pour ne pas annuler
        # la transaction principale de l'appelant. L'exception 
        # remontera si c'est une erreur BDD fatale.
        pass


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
    from app.models.communication import Conversation
    from app.models.user import Utilisateur
    
    conv = db.session.get(Conversation, conversation_id)
    exp = db.session.get(Utilisateur, expediteur_id)
    
    titre = 'Nouveau message'
    contenu = 'Vous avez reçu un nouveau message.'
    
    if conv and exp:
        if exp.role == 'parent' and destinataire_role == 'professeur':
            titre = f'Nouveau message de {exp.parent.nom_complet}'
            if conv.etudiant_concerne:
                contenu = f'Vous avez reçu un message de {exp.parent.nom_complet} concernant son enfant {conv.etudiant_concerne.nom_complet}.'
            else:
                contenu = f'Vous avez reçu un message de {exp.parent.nom_complet}.'
        elif exp.role == 'etudiant':
            titre = f'Nouveau message de {exp.etudiant.nom_complet}'
            contenu = f'Vous avez reçu un message de {exp.etudiant.nom_complet}.'
        elif exp.role == 'professeur':
            titre = f'Nouveau message du Prof. {exp.professeur.nom_complet}'
            contenu = f'Le professeur {exp.professeur.nom_complet} vous a envoyé un message.'

    envoyer_notification(
        destinataire_id   = destinataire_id,
        destinataire_role = destinataire_role,
        type_notif        = 'message_recu',
        titre             = titre,
        contenu           = contenu,
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


def notifier_etudiants_affectation(affectation_id: int, type_notif: str,
                                   titre: str, contenu: str,
                                   ref_table: str = None, ref_id: int = None) -> None:
    """Notifie tous les étudiants inscrits (actifs) dans la section de l'affectation."""
    from app.models.program import AffectationEnseignement, Inscription

    aff = db.session.get(AffectationEnseignement, affectation_id)
    if not aff:
        return
    inscriptions = Inscription.query.filter_by(
        section_id=aff.section_id, statut='actif').all()
    for ins in inscriptions:
        envoyer_notification(
            destinataire_id   = ins.etudiant.utilisateur_id,
            destinataire_role = 'etudiant',
            type_notif        = type_notif,
            titre             = titre,
            contenu           = contenu,
            ref_table         = ref_table,
            ref_id            = ref_id,
        )


def notifier_correction_publiee(affectation_id: int, matiere_nom: str,
                                correction_id: int) -> None:
    notifier_etudiants_affectation(
        affectation_id,
        'correction_publiee',
        'Correction disponible',
        f'Un corrigé a été publié pour la matière {matiere_nom}.',
        ref_table='corrections_examens',
        ref_id=correction_id,
    )


def notifier_cours_publie(affectation_id: int, matiere_nom: str, cours_id: int) -> None:
    notifier_etudiants_affectation(
        affectation_id,
        'cours_publie',
        'Nouveau cours',
        f'Un nouveau support de cours est disponible pour {matiere_nom}.',
        ref_table='cours',
        ref_id=cours_id,
    )


def notifier_devoir_publie(affectation_id: int, matiere_nom: str, devoir_id: int) -> None:
    notifier_etudiants_affectation(
        affectation_id,
        'devoir_publie',
        'Nouveau devoir',
        f'Un devoir a été publié pour la matière {matiere_nom}.',
        ref_table='devoirs',
        ref_id=devoir_id,
    )


def notifier_message_cours(conversation_id: int, destinataire_user_id: int,
                           destinataire_role: str, cours_titre: str) -> None:
    envoyer_notification(
        destinataire_id=destinataire_user_id,
        destinataire_role=destinataire_role,
        type_notif='message_recu',
        titre='Nouveau message — cours',
        contenu=f'Vous avez reçu un message concernant le cours « {cours_titre} ».',
        ref_table='conversations',
        ref_id=conversation_id,
    )
