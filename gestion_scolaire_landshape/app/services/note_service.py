# =============================================================
#  EduNova — services/note_service.py
#  Calcul des moyennes, résultats semestriels et annuels
# =============================================================
from datetime import datetime, timezone
from app.extensions import db
from app.utils.helpers import get_param_float, mention_from_moyenne


def calculer_moyenne_matiere(note_obj) -> float | None:
    """Calcule la moyenne d'une Note selon les coefficients configurés."""
    d1 = float(note_obj.devoir1) if note_obj.devoir1 is not None else None
    d2 = float(note_obj.devoir2) if note_obj.devoir2 is not None else None
    cc = float(note_obj.evaluation_continue) if note_obj.evaluation_continue is not None else None
    ex = float(note_obj.examen) if note_obj.examen is not None else None

    if d1 is None or d2 is None or cc is None or ex is None:
        return None
        
    # Formula: ( ((F1+F2+CC)/3) + (2*Examen) ) / 3
    moy = (((d1 + d2 + cc) / 3.0) + (2.0 * ex)) / 3.0
    return round(moy, 2)


def calculer_moyenne_semestre(etudiant_id: int, inscription_id: int, semestre_id: int) -> float | None:
    """
    Calcule la moyenne générale d'un semestre :
    somme (moyenne_matiere × coefficient_programme) / somme(coefficients).
    """
    from app.models.evaluation    import Note
    from app.models.program       import AffectationEnseignement, Programme
    from app.models.academic      import Semestre
    from app.models.program       import Inscription

    insc  = db.session.get(Inscription, inscription_id)
    sem   = db.session.get(Semestre, semestre_id)
    if not insc or not sem:
        return None

    # Récupérer toutes les notes de cet étudiant pour ce semestre
    notes = (
        db.session.query(Note, Programme.coefficient)
        .join(AffectationEnseignement, Note.affectation_id == AffectationEnseignement.id)
        .join(Programme, (Programme.matiere_id     == AffectationEnseignement.matiere_id)
                       & (Programme.specialite_id  == insc.section.specialite_id)
                       & (Programme.niveau_id      == insc.section.niveau_id)
                       & (Programme.semestre_numero == sem.numero))
        .filter(Note.etudiant_id     == etudiant_id,
                AffectationEnseignement.semestre_id == semestre_id)
        .all()
    )

    if not notes:
        return None

    total_pond  = 0.0
    total_coeff = 0.0
    for note, coeff in notes:
        moy = calculer_moyenne_matiere(note)
        if moy is None:
            return None   # Toutes les notes doivent être saisies
        total_pond  += moy * coeff
        total_coeff += coeff

    if total_coeff == 0:
        return None
    return round(total_pond / total_coeff, 2)


def enregistrer_resultat_semestre(etudiant_id: int, inscription_id: int, semestre_id: int) -> bool:
    """Calcule et enregistre (ou met à jour) le ResultatSemestre."""
    from app.models.evaluation import ResultatSemestre

    moy = calculer_moyenne_semestre(etudiant_id, inscription_id, semestre_id)
    if moy is None:
        return False

    rs = ResultatSemestre.query.filter_by(
        etudiant_id=etudiant_id,
        inscription_id=inscription_id,
        semestre_id=semestre_id
    ).first()

    if not rs:
        rs = ResultatSemestre(
            etudiant_id=etudiant_id,
            inscription_id=inscription_id,
            semestre_id=semestre_id,
        )
        db.session.add(rs)

    rs.moyenne_generale = moy
    rs.mention          = mention_from_moyenne(moy)
    rs.est_calcule      = True
    rs.date_calcul      = datetime.now(timezone.utc)
    db.session.commit()
    return True


def enregistrer_resultat_annuel(etudiant_id: int, inscription_id: int, annee_scolaire_id: int) -> bool:
    """Calcule le résultat annuel si les deux semestres sont clôturés."""
    from app.models.evaluation import ResultatSemestre, ResultatAnnuel
    from app.models.program    import Inscription
    from app.models.academic   import Semestre

    insc  = db.session.get(Inscription, inscription_id)
    if not insc:
        return False

    sems = Semestre.query.filter_by(annee_scolaire_id=annee_scolaire_id).all()
    moys = {}
    for sem in sems:
        rs = ResultatSemestre.query.filter_by(
            etudiant_id=etudiant_id,
            inscription_id=inscription_id,
            semestre_id=sem.id
        ).first()
        if rs and rs.est_calcule:
            moys[sem.numero] = float(rs.moyenne_generale)

    if 1 not in moys or 2 not in moys:
        return False

    moy_ann = round((moys[1] + moys[2]) / 2, 2)
    seuil   = get_param_float('seuil_passage', 10.0)

    ra = ResultatAnnuel.query.filter_by(
        etudiant_id=etudiant_id,
        annee_scolaire_id=annee_scolaire_id
    ).first()

    if not ra:
        ra = ResultatAnnuel(
            etudiant_id=etudiant_id,
            inscription_id=inscription_id,
            annee_scolaire_id=annee_scolaire_id,
        )
        db.session.add(ra)

    ra.moyenne_s1       = moys[1]
    ra.moyenne_s2       = moys[2]
    ra.moyenne_annuelle = moy_ann
    ra.mention          = mention_from_moyenne(moy_ann)
    ra.decision         = 'admis' if moy_ann >= seuil else 'redoublant'
    ra.est_calcule      = True
    ra.date_calcul      = datetime.now(timezone.utc)
    db.session.commit()
    return True


def sauvegarder_note(etudiant_id: int, affectation_id: int, professeur_id: int,
                      d1=None, d2=None, ec=None, examen=None, observations: str = '') -> bool:
    """Crée ou met à jour une note, puis recalcule la moyenne."""
    from app.models.evaluation import Note

    note = Note.query.filter_by(etudiant_id=etudiant_id, affectation_id=affectation_id).first()
    if not note:
        note = Note(etudiant_id=etudiant_id, affectation_id=affectation_id, saisie_par=professeur_id)
        db.session.add(note)

    if d1      is not None: note.devoir1             = float(d1)
    if d2      is not None: note.devoir2             = float(d2)
    if ec      is not None: note.evaluation_continue = float(ec)
    if examen  is not None: note.examen              = float(examen)
    note.saisie_par  = professeur_id
    note.observations = observations

    moy = calculer_moyenne_matiere(note)
    if moy is not None:
        note.moyenne = moy

    db.session.commit()
    return True
