# =============================================================
#  EduNova — models/program.py
#  Programme: Matiere, Programme (matiere×specialite×niveau×sem)
#             Inscription, AffectationEnseignement
# =============================================================
from datetime import datetime, timezone
from app.extensions import db


class Matiere(db.Model):
    __tablename__ = 'matieres'

    id          = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    code        = db.Column(db.String(20),  nullable=False,   unique=True)
    nom         = db.Column(db.String(150), nullable=False)
    nom_ar      = db.Column(db.String(150), nullable=True)
    nom_en      = db.Column(db.String(150), nullable=True)
    description = db.Column(db.Text,        nullable=True)
    est_active  = db.Column(db.Boolean,     nullable=False,   default=True)
    created_at  = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))
    updated_at  = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))

    programmes   = db.relationship('Programme',              back_populates='matiere',   lazy='dynamic')
    affectations = db.relationship('AffectationEnseignement', back_populates='matiere',  lazy='dynamic')
    conversations = db.relationship('Conversation',           back_populates='matiere',  lazy='dynamic')

    def __repr__(self):
        return f'<Matiere {self.code} — {self.nom}>'


class Programme(db.Model):
    """Matière enseignée dans une spécialité/niveau/semestre + coefficient."""
    __tablename__ = 'programme'

    id                   = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    matiere_id           = db.Column(db.Integer,      db.ForeignKey('matieres.id',    ondelete='RESTRICT'), nullable=False)
    specialite_id        = db.Column(db.Integer,      db.ForeignKey('specialites.id', ondelete='RESTRICT'), nullable=False)
    niveau_id            = db.Column(db.Integer,      db.ForeignKey('niveaux.id',     ondelete='RESTRICT'), nullable=False)
    semestre_numero      = db.Column(db.SmallInteger, nullable=False)   # 1 ou 2
    coefficient          = db.Column(db.SmallInteger, nullable=False,   default=1)
    type_matiere         = db.Column(db.Enum('principale', 'secondaire'), nullable=False, default='principale')
    volume_horaire_hebdo = db.Column(db.Numeric(4, 1), nullable=True)
    est_actif            = db.Column(db.Boolean,      nullable=False,   default=True)

    matiere    = db.relationship('Matiere',    back_populates='programmes')
    specialite = db.relationship('Specialite', back_populates='programmes')
    niveau     = db.relationship('Niveau',     back_populates='programmes')

    __table_args__ = (
        db.UniqueConstraint('matiere_id', 'specialite_id', 'niveau_id', 'semestre_numero',
                            name='uk_programme'),
    )

    def __repr__(self):
        return (f'<Programme mat={self.matiere_id} spe={self.specialite_id} '
                f'niv={self.niveau_id} sem={self.semestre_numero}>')


class Inscription(db.Model):
    """Inscription annuelle d'un étudiant dans une section."""
    __tablename__ = 'inscriptions'

    id                = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    etudiant_id       = db.Column(db.Integer,      db.ForeignKey('etudiants.id',       ondelete='RESTRICT'), nullable=False)
    section_id        = db.Column(db.Integer,      db.ForeignKey('sections.id',        ondelete='RESTRICT'), nullable=False)
    annee_scolaire_id = db.Column(db.Integer,      db.ForeignKey('annees_scolaires.id', ondelete='RESTRICT'), nullable=False)
    date_inscription  = db.Column(db.Date,         nullable=False)
    semestre_courant  = db.Column(db.SmallInteger, nullable=False,   default=1)
    statut            = db.Column(db.Enum('actif', 'exclu', 'transfere', 'diplome'), nullable=False, default='actif')
    date_fin          = db.Column(db.Date,         nullable=True)
    motif_fin         = db.Column(db.Text,         nullable=True)
    created_at        = db.Column(db.DateTime,     default=lambda: datetime.now(timezone.utc))
    updated_at        = db.Column(db.DateTime,     default=lambda: datetime.now(timezone.utc),
                                   onupdate=lambda: datetime.now(timezone.utc))

    etudiant          = db.relationship('Etudiant',       back_populates='inscriptions')
    section           = db.relationship('Section',        back_populates='inscriptions')
    annee_scolaire    = db.relationship('AnneeScolaire',  back_populates='inscriptions')
    resultats_semestre = db.relationship('ResultatSemestre', back_populates='inscription', lazy='dynamic')
    resultat_annuel   = db.relationship('ResultatAnnuel', back_populates='inscription', uselist=False)
    compteur_absences = db.relationship('CompteurAbsences', back_populates='inscription', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('etudiant_id', 'annee_scolaire_id', name='uk_ins'),
    )

    def __repr__(self):
        return f'<Inscription etu={self.etudiant_id} sec={self.section_id}>'


class AffectationEnseignement(db.Model):
    """Professeur ↔ Matière ↔ Section ↔ Semestre."""
    __tablename__ = 'affectations_enseignement'

    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    professeur_id   = db.Column(db.Integer, db.ForeignKey('professeurs.id', ondelete='RESTRICT'), nullable=False)
    matiere_id      = db.Column(db.Integer, db.ForeignKey('matieres.id',    ondelete='RESTRICT'), nullable=False)
    section_id      = db.Column(db.Integer, db.ForeignKey('sections.id',    ondelete='RESTRICT'), nullable=False)
    semestre_id     = db.Column(db.Integer, db.ForeignKey('semestres.id',   ondelete='RESTRICT'), nullable=False)
    date_affectation = db.Column(db.Date,   nullable=True)
    est_active      = db.Column(db.Boolean, nullable=False, default=True)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    professeur     = db.relationship('Professeur',   back_populates='affectations')
    matiere        = db.relationship('Matiere',       back_populates='affectations')
    section        = db.relationship('Section',       back_populates='affectations')
    semestre       = db.relationship('Semestre',      back_populates='affectations')
    notes          = db.relationship('Note',          back_populates='affectation',       lazy='dynamic')
    seances        = db.relationship('Seance',        back_populates='affectation',       lazy='dynamic')
    cours          = db.relationship('Cours',         back_populates='affectation',       lazy='dynamic')
    devoirs        = db.relationship('Devoir',        back_populates='affectation',       lazy='dynamic')
    corrections    = db.relationship('CorrectionExamen', back_populates='affectation',    lazy='dynamic')
    emploi_du_temps = db.relationship('EmploiDuTemps', back_populates='affectation',     lazy='dynamic')
    calendrier_examens = db.relationship('CalendrierExamen', back_populates='affectation', lazy='dynamic')
    posts          = db.relationship('PostProfesseur', back_populates='affectation',      lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('matiere_id', 'section_id', 'semestre_id', name='uk_affectation'),
    )

    def __repr__(self):
        return (f'<Affectation prof={self.professeur_id} mat={self.matiere_id} '
                f'sec={self.section_id} sem={self.semestre_id}>')
