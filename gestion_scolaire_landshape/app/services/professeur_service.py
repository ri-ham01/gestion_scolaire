# =============================================================
#  EduNova — services/professeur_service.py
#  Spécialité professeur, suppression définitive
# =============================================================
from app.extensions import db


def infer_specialite_code_from_username(username: str) -> str | None:
    import re
    m = re.match(r'^prof_([a-zA-Z]+)\d+$', username or '')
    return m.group(1).lower() if m else None


def resoudre_specialite_professeur(prof):
    """Retourne l'objet Specialite du professeur (username ou affectation)."""
    from app.models.academic import Specialite
    from app.models.program import AffectationEnseignement

    user = prof.utilisateur
    if user:
        code = infer_specialite_code_from_username(user.username)
        if code:
            spe = Specialite.query.filter_by(code=code).first()
            if not spe:
                spe = Specialite.query.filter(Specialite.code.ilike(code)).first()
            if spe:
                return spe

    aff = (
        AffectationEnseignement.query.filter_by(professeur_id=prof.id, est_active=True)
        .first()
    )
    if aff and aff.section and aff.section.specialite:
        return aff.section.specialite
    return None


def supprimer_professeur_definitif(prof_id: int) -> None:
    """Supprime le professeur, son compte utilisateur et les données associées."""
    from app.models.profiles import Professeur
    from app.models.program import AffectationEnseignement
    from app.models.evaluation import Note, CorrectionExamen
    from app.models.pedagogy import (Cours, Devoir, SoumissionDevoir, PostProfesseur,
                                     CommentairePost, CoursConsulte)
    from app.models.presence import Seance, Presence
    from app.models.communication import Conversation, Message

    prof = db.session.get(Professeur, prof_id)
    if not prof:
        return

    aff_ids = [a.id for a in AffectationEnseignement.query.filter_by(professeur_id=prof.id).all()]

    if aff_ids:
        cours_ids = [c.id for c in Cours.query.filter(Cours.affectation_id.in_(aff_ids)).all()]
        if cours_ids:
            CoursConsulte.query.filter(CoursConsulte.cours_id.in_(cours_ids)).delete(
                synchronize_session=False)
            conv_ids = [c.id for c in Conversation.query.filter(
                Conversation.cours_id.in_(cours_ids)).all()]
            if conv_ids:
                Message.query.filter(Message.conversation_id.in_(conv_ids)).delete(
                    synchronize_session=False)
                Conversation.query.filter(Conversation.id.in_(conv_ids)).delete(
                    synchronize_session=False)

        devoir_ids = [d.id for d in Devoir.query.filter(Devoir.affectation_id.in_(aff_ids)).all()]
        if devoir_ids:
            SoumissionDevoir.query.filter(SoumissionDevoir.devoir_id.in_(devoir_ids)).delete(
                synchronize_session=False)

        Devoir.query.filter(Devoir.affectation_id.in_(aff_ids)).delete(synchronize_session=False)
        Cours.query.filter(Cours.affectation_id.in_(aff_ids)).delete(synchronize_session=False)
        CorrectionExamen.query.filter(CorrectionExamen.affectation_id.in_(aff_ids)).delete(
            synchronize_session=False)
        Note.query.filter(Note.affectation_id.in_(aff_ids)).delete(synchronize_session=False)

        seance_ids = [s.id for s in Seance.query.filter(Seance.affectation_id.in_(aff_ids)).all()]
        if seance_ids:
            Presence.query.filter(Presence.seance_id.in_(seance_ids)).delete(synchronize_session=False)
            Seance.query.filter(Seance.id.in_(seance_ids)).delete(synchronize_session=False)

        AffectationEnseignement.query.filter(AffectationEnseignement.id.in_(aff_ids)).delete(
            synchronize_session=False)

    CorrectionExamen.query.filter_by(publie_par=prof.id).delete(synchronize_session=False)
    Cours.query.filter_by(publie_par=prof.id).delete(synchronize_session=False)
    Devoir.query.filter_by(publie_par=prof.id).delete(synchronize_session=False)
    Note.query.filter_by(saisie_par=prof.id).delete(synchronize_session=False)
    Presence.query.filter_by(enregistre_par=prof.id).delete(synchronize_session=False)

    for post in PostProfesseur.query.filter_by(professeur_id=prof.id).all():
        CommentairePost.query.filter_by(post_id=post.id).delete(synchronize_session=False)
    PostProfesseur.query.filter_by(professeur_id=prof.id).delete(synchronize_session=False)

    user_id = prof.utilisateur_id
    db.session.delete(prof)
    db.session.flush()

    from app.models.user import Utilisateur
    user = db.session.get(Utilisateur, user_id)
    if user:
        db.session.delete(user)
