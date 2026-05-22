# =============================================================
#  EduNova — models/evaluation.py
#  Notes, ResultatSemestre, ResultatAnnuel, ReleverNotes,
#  CorrectionExamen
# =============================================================
from datetime import datetime, timezone
from app.extensions import db


class Note(db.Model):
    __tablename__ = 'notes'

    id                   = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    etudiant_id          = db.Column(db.Integer,      db.ForeignKey('etudiants.id',                  ondelete='RESTRICT'), nullable=False)
    affectation_id       = db.Column(db.Integer,      db.ForeignKey('affectations_enseignement.id',  ondelete='RESTRICT'), nullable=False)
    devoir1              = db.Column(db.Numeric(5, 2), nullable=True)
    devoir2              = db.Column(db.Numeric(5, 2), nullable=True)
    examen               = db.Column(db.Numeric(5, 2), nullable=True)
    evaluation_continue  = db.Column(db.Numeric(5, 2), nullable=True)
    moyenne              = db.Column(db.Numeric(5, 2), nullable=True)
    saisie_par           = db.Column(db.Integer,      db.ForeignKey('professeurs.id',  ondelete='RESTRICT'), nullable=False)
    date_saisie          = db.Column(db.DateTime,     default=lambda: datetime.now(timezone.utc))
    est_validee          = db.Column(db.Boolean,      nullable=False, default=False)
    date_validation      = db.Column(db.DateTime,     nullable=True)
    validee_par          = db.Column(db.Integer,      db.ForeignKey('administrateurs.id', ondelete='SET NULL'), nullable=True)
    observations         = db.Column(db.Text,         nullable=True)

    etudiant             = db.relationship('Etudiant',               back_populates='notes')
    affectation          = db.relationship('AffectationEnseignement', back_populates='notes')
    professeur_saisie    = db.relationship('Professeur',              back_populates='notes_saisies',
                                           foreign_keys=[saisie_par])

    __table_args__ = (
        db.UniqueConstraint('etudiant_id', 'affectation_id', name='uk_note'),
    )

    def __repr__(self):
        return f'<Note etu={self.etudiant_id} aff={self.affectation_id} moy={self.moyenne}>'

    def calculer_moyenne(self) -> float | None:
        """
        Calcule la moyenne selon la formule :
        Moyenne = ( ((Devoir1 + Devoir2 + EvalContinue) / 3) + (2 * Examen) ) / 3
        Retourne None si l'un des composants est manquant.
        """
        d1 = float(self.devoir1) if self.devoir1 is not None else None
        d2 = float(self.devoir2) if self.devoir2 is not None else None
        cc = float(self.evaluation_continue) if self.evaluation_continue is not None else None
        ex = float(self.examen) if self.examen is not None else None

        if d1 is None or d2 is None or cc is None or ex is None:
            return None

        # Formula: (((d1 + d2 + cc)/3) + 2*ex) / 3
        moy = (((d1 + d2 + cc) / 3.0) + (2.0 * ex)) / 3.0
        return round(moy, 2)

    def sauvegarder_avec_calcul(self):
        """Met à jour self.moyenne puis pousse l'instance dans la session."""
        self.moyenne = self.calculer_moyenne()
        db.session.add(self)


class ResultatSemestre(db.Model):
    __tablename__ = 'resultats_semestre'

    id               = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    etudiant_id      = db.Column(db.Integer,      db.ForeignKey('etudiants.id',    ondelete='RESTRICT'), nullable=False)
    inscription_id   = db.Column(db.Integer,      db.ForeignKey('inscriptions.id', ondelete='RESTRICT'), nullable=False)
    semestre_id      = db.Column(db.Integer,      db.ForeignKey('semestres.id',    ondelete='RESTRICT'), nullable=False)
    moyenne_generale = db.Column(db.Numeric(5, 2), nullable=True)
    rang             = db.Column(db.SmallInteger,  nullable=True)
    mention          = db.Column(db.String(50),    nullable=True)
    observations     = db.Column(db.Text,          nullable=True)
    est_calcule      = db.Column(db.Boolean,       nullable=False, default=False)
    date_calcul      = db.Column(db.DateTime,      nullable=True)

    etudiant     = db.relationship('Etudiant',    foreign_keys=[etudiant_id])
    inscription  = db.relationship('Inscription', back_populates='resultats_semestre')
    semestre     = db.relationship('Semestre',    back_populates='resultats_semestre')

    __table_args__ = (
        db.UniqueConstraint('etudiant_id', 'inscription_id', 'semestre_id', name='uk_res_sem'),
    )

    def __repr__(self):
        return f'<ResultatSemestre etu={self.etudiant_id} sem={self.semestre_id} moy={self.moyenne_generale}>'

    @property
    def mention_label(self) -> str:
        if self.moyenne_generale is None:
            return '—'
        moy = float(self.moyenne_generale)
        if moy >= 16: return 'Très Bien'
        if moy >= 14: return 'Bien'
        if moy >= 12: return 'Assez Bien'
        if moy >= 10: return 'Passable'
        return 'Insuffisant'


class ResultatAnnuel(db.Model):
    __tablename__ = 'resultats_annuels'

    id                    = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    etudiant_id           = db.Column(db.Integer,      db.ForeignKey('etudiants.id',        ondelete='RESTRICT'), nullable=False)
    inscription_id        = db.Column(db.Integer,      db.ForeignKey('inscriptions.id',     ondelete='RESTRICT'), nullable=False)
    annee_scolaire_id     = db.Column(db.Integer,      db.ForeignKey('annees_scolaires.id', ondelete='RESTRICT'), nullable=False)
    moyenne_s1            = db.Column(db.Numeric(5, 2), nullable=True)
    moyenne_s2            = db.Column(db.Numeric(5, 2), nullable=True)
    moyenne_annuelle      = db.Column(db.Numeric(5, 2), nullable=True)
    rang_annuel           = db.Column(db.SmallInteger,  nullable=True)
    decision              = db.Column(db.Enum('en_attente', 'admis', 'redoublant', 'exclu', 'diplome'),
                                      nullable=False, default='en_attente')
    mention               = db.Column(db.String(50),    nullable=True)
    observations          = db.Column(db.Text,          nullable=True)
    est_calcule           = db.Column(db.Boolean,       nullable=False, default=False)
    date_calcul           = db.Column(db.DateTime,      nullable=True)
    prochaine_section_id  = db.Column(db.Integer,      db.ForeignKey('sections.id', ondelete='SET NULL'), nullable=True)

    etudiant       = db.relationship('Etudiant',       foreign_keys=[etudiant_id])
    inscription    = db.relationship('Inscription',    back_populates='resultat_annuel')
    annee_scolaire = db.relationship('AnneeScolaire',  foreign_keys=[annee_scolaire_id])

    __table_args__ = (
        db.UniqueConstraint('etudiant_id', 'annee_scolaire_id', name='uk_res_an'),
    )

    def __repr__(self):
        return f'<ResultatAnnuel etu={self.etudiant_id} dec={self.decision} moy={self.moyenne_annuelle}>'

    def calculer_et_decider(self):
        """Calcule la moyenne annuelle et prononce la décision de passage."""
        from app.utils.helpers import get_param_float
        seuil = get_param_float('seuil_passage', 10.0)
        if self.moyenne_s1 is not None and self.moyenne_s2 is not None:
            self.moyenne_annuelle = round((float(self.moyenne_s1) + float(self.moyenne_s2)) / 2, 2)
            self.est_calcule = True
            self.date_calcul = datetime.now(timezone.utc)
            if float(self.moyenne_annuelle) >= seuil:
                self.decision = 'admis'
            else:
                self.decision = 'redoublant'
        db.session.add(self)


class ReleverNotes(db.Model):
    __tablename__ = 'releves_notes'

    id                = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    etudiant_id       = db.Column(db.Integer,     db.ForeignKey('etudiants.id',        ondelete='RESTRICT'), nullable=False)
    annee_scolaire_id = db.Column(db.Integer,     db.ForeignKey('annees_scolaires.id', ondelete='RESTRICT'), nullable=False)
    semestre_id       = db.Column(db.Integer,     db.ForeignKey('semestres.id',        ondelete='SET NULL'),  nullable=True)
    type              = db.Column(db.Enum('semestre', 'annuel'), nullable=False)
    fichier_url       = db.Column(db.String(500), nullable=False)
    nom_fichier       = db.Column(db.String(255), nullable=True)
    taille_fichier_ko = db.Column(db.Integer,     nullable=True)
    qr_code_token     = db.Column(db.String(64),  nullable=True,    unique=True)
    qr_code_image_url = db.Column(db.String(500), nullable=True)
    genere_par        = db.Column(db.Integer,     db.ForeignKey('administrateurs.id', ondelete='SET NULL'), nullable=True)
    date_generation   = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))

    etudiant       = db.relationship('Etudiant',      foreign_keys=[etudiant_id])
    annee_scolaire = db.relationship('AnneeScolaire',  foreign_keys=[annee_scolaire_id])
    semestre       = db.relationship('Semestre',       foreign_keys=[semestre_id])

    def __repr__(self):
        return f'<ReleverNotes etu={self.etudiant_id} type={self.type}>'


class CorrectionExamen(db.Model):
    __tablename__ = 'corrections_examens'

    id                   = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    affectation_id       = db.Column(db.Integer,     db.ForeignKey('affectations_enseignement.id', ondelete='RESTRICT'), nullable=False)
    type_evaluation      = db.Column(db.Enum('devoir1', 'devoir2', 'examen', 'evaluation_continue'), nullable=False)
    titre                = db.Column(db.String(255), nullable=False)
    description          = db.Column(db.Text,        nullable=True)
    fichier_url          = db.Column(db.String(500), nullable=False)
    type_fichier         = db.Column(db.Enum('pdf', 'word', 'image', 'autre'), nullable=False)
    nom_fichier_original = db.Column(db.String(255), nullable=True)
    taille_fichier_ko    = db.Column(db.Integer,     nullable=True)
    est_publie           = db.Column(db.Boolean,     nullable=False, default=False)
    date_publication     = db.Column(db.DateTime,    nullable=True)
    publie_par           = db.Column(db.Integer,     db.ForeignKey('professeurs.id', ondelete='RESTRICT'), nullable=False)
    created_at           = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))
    updated_at           = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc),
                                      onupdate=lambda: datetime.now(timezone.utc))

    affectation = db.relationship('AffectationEnseignement', back_populates='corrections')
    professeur  = db.relationship('Professeur',              foreign_keys=[publie_par])

    __table_args__ = (
        db.UniqueConstraint('affectation_id', 'type_evaluation', name='uk_correction'),
    )

    def __repr__(self):
        return f'<CorrectionExamen aff={self.affectation_id} type={self.type_evaluation}>'
