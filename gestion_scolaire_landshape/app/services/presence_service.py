# =============================================================
#  EduNova — services/presence_service.py
#  Logique métier pour les présences et compteurs d'absences
# =============================================================
from datetime import datetime, timezone
from app.extensions import db


def enregistrer_seance_et_presences(aff_id: int, prof_id: int,
                                      date_seance, heure_debut, heure_fin,
                                      type_seance: str,
                                      data: list):
    """
    Crée une séance et enregistre les présences.
    data = [{'etudiant_id': int, 'statut': str}, ...]
    Retourne la Seance créée.
    """
    from app.models.presence import Seance, Presence
    from app.services.notif_service import notifier_absence

    seance = Seance(
        affectation_id = aff_id,
        date_seance    = date_seance,
        heure_debut    = heure_debut,
        heure_fin      = heure_fin,
        type_seance    = type_seance,
    )
    db.session.add(seance)
    db.session.flush()

    for item in data:
        etu_id = item['etudiant_id']
        statut = item['statut']

        pres = Presence(
            seance_id       = seance.id,
            etudiant_id     = etu_id,
            statut          = statut,
            enregistre_par  = prof_id,
        )
        db.session.add(pres)

        if statut == 'absent':
            _maj_compteur(etu_id, aff_id, justifie=False)
            notifier_absence(etu_id, seance.id)

    db.session.commit()
    return seance


def _maj_compteur(etudiant_id: int, aff_id: int, justifie: bool) -> None:
    """Met à jour le compteur d'absences et vérifie le seuil d'exclusion."""
    from app.models.presence import CompteurAbsences
    from app.models.program  import Inscription, AffectationEnseignement

    aff  = db.session.get(AffectationEnseignement, aff_id)
    insc = Inscription.query.filter_by(
        etudiant_id=etudiant_id, statut='actif').first()
    if not insc:
        return

    cpt = CompteurAbsences.query.filter_by(
        etudiant_id=etudiant_id,
        inscription_id=insc.id,
        semestre_id=aff.semestre_id,
    ).first()
    if not cpt:
        cpt = CompteurAbsences(
            etudiant_id    = etudiant_id,
            inscription_id = insc.id,
            semestre_id    = aff.semestre_id,
        )
        db.session.add(cpt)
        db.session.flush()

    cpt.total_seances += 1
    cpt.incrementer_absence(justifie)

    # Vérifier seuil d'exclusion
    seuil = _get_seuil()
    if (not cpt.est_exclu
            and cpt.absences_non_justifiees >= seuil):
        cpt.est_exclu       = True
        cpt.date_exclusion  = datetime.now(timezone.utc)
        insc.statut         = 'exclu'
        _notifier_exclusion(etudiant_id)


def _get_seuil() -> int:
    """Récupère le seuil d'exclusion depuis les paramètres système."""
    try:
        from app.models.academic import ParametreSysteme
        p = ParametreSysteme.query.filter_by(
            cle='seuil_exclusion_absences').first()
        return int(p.valeur) if p else 10
    except Exception:
        return 10


def _notifier_exclusion(etudiant_id: int) -> None:
    from app.models.profiles import Etudiant, ParentEtudiant
    from app.services.notif_service import envoyer_notification
    etu = db.session.get(Etudiant, etudiant_id)
    if not etu:
        return
    envoyer_notification(
        destinataire_id   = etu.utilisateur_id,
        destinataire_role = 'etudiant',
        type_notif        = 'exclusion_absences',
        titre             = 'Exclusion automatique',
        contenu           = 'Vous avez atteint le seuil d\'absences non justifiées. Votre inscription a été suspendue.',
    )
    for link in ParentEtudiant.query.filter_by(etudiant_id=etudiant_id).all():
        envoyer_notification(
            destinataire_id   = link.parent.utilisateur_id,
            destinataire_role = 'parent',
            type_notif        = 'exclusion_absences',
            titre             = f'Exclusion de {etu.nom_complet}',
            contenu           = f'{etu.nom_complet} a été exclu(e) suite au dépassement du seuil d\'absences.',
        )


def accepter_justification(presence_id: int, admin_id: int) -> bool:
    """Accepte une justification d'absence — décrémente le compteur."""
    from app.models.presence import Presence, CompteurAbsences
    from app.models.program  import Inscription

    pres = db.session.get(Presence, presence_id)
    if not pres or pres.statut_justification != 'en_attente':
        return False

    pres.statut_justification  = 'acceptee'
    pres.traite_par_admin_id   = admin_id
    pres.date_traitement       = datetime.now(timezone.utc)
    pres.statut                = 'excuse'

    # Décrémente les absences non justifiées
    insc = Inscription.query.filter_by(
        etudiant_id=pres.etudiant_id, statut='actif').first()
    if insc and pres.seance:
        cpt = CompteurAbsences.query.filter_by(
            etudiant_id=pres.etudiant_id,
            inscription_id=insc.id,
            semestre_id=pres.seance.affectation.semestre_id,
        ).first()
        if cpt and cpt.absences_non_justifiees > 0:
            cpt.absences_non_justifiees -= 1
            cpt.absences_justifiees     += 1

    db.session.commit()
    return True


def refuser_justification(presence_id: int, admin_id: int) -> bool:
    """Refuse une justification — l'absence reste non justifiée."""
    from app.models.presence import Presence

    pres = db.session.get(Presence, presence_id)
    if not pres or pres.statut_justification != 'en_attente':
        return False

    pres.statut_justification = 'refusee'
    pres.traite_par_admin_id  = admin_id
    pres.date_traitement      = datetime.now(timezone.utc)
    db.session.commit()
    return True
