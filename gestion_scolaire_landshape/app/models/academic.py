# =============================================================
#  EduNova — models/academic.py
#  Structure académique : AnneeScolaire, Semestre, Niveau,
#                         Specialite, Section
# =============================================================
from datetime import datetime, timezone
from app.extensions import db


class AnneeScolaire(db.Model):
    __tablename__ = 'annees_scolaires'

    id          = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    label       = db.Column(db.String(20),   nullable=False,   unique=True)   # ex: 2024-2025
    annee_debut = db.Column(db.SmallInteger, nullable=False)
    annee_fin   = db.Column(db.SmallInteger, nullable=False)
    date_debut  = db.Column(db.Date,         nullable=True)
    date_fin    = db.Column(db.Date,         nullable=True)
    est_active  = db.Column(db.Boolean,      nullable=False,   default=False)
    created_at  = db.Column(db.DateTime,     default=lambda: datetime.now(timezone.utc))

    # Relationships
    semestres  = db.relationship('Semestre',    back_populates='annee_scolaire', lazy='dynamic')
    sections   = db.relationship('Section',     back_populates='annee_scolaire', lazy='dynamic')
    inscriptions = db.relationship('Inscription', back_populates='annee_scolaire', lazy='dynamic')

    def __repr__(self):
        return f'<AnneeScolaire {self.label}>'

    @staticmethod
    def get_active():
        return AnneeScolaire.query.filter_by(est_active=True).first()


class Semestre(db.Model):
    __tablename__ = 'semestres'

    id                = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    annee_scolaire_id = db.Column(db.Integer,     db.ForeignKey('annees_scolaires.id', ondelete='RESTRICT'), nullable=False)
    numero            = db.Column(db.SmallInteger, nullable=False)   # 1 ou 2
    date_debut        = db.Column(db.Date,         nullable=False)
    date_fin          = db.Column(db.Date,         nullable=False)
    est_actif         = db.Column(db.Boolean,      nullable=False,  default=False)
    notes_cloturees   = db.Column(db.Boolean,      nullable=False,  default=False)

    # Relationships
    annee_scolaire      = db.relationship('AnneeScolaire',   back_populates='semestres')
    affectations        = db.relationship('AffectationEnseignement', back_populates='semestre', lazy='dynamic')
    resultats_semestre  = db.relationship('ResultatSemestre', back_populates='semestre', lazy='dynamic')
    calendrier_examens  = db.relationship('CalendrierExamen', back_populates='semestre', lazy='dynamic')
    emploi_du_temps     = db.relationship('EmploiDuTemps',    back_populates='semestre', lazy='dynamic')
    pdfs_emplois_temps  = db.relationship('PdfEmploiTemps',   back_populates='semestre', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('annee_scolaire_id', 'numero', name='uk_annee_sem'),
    )

    def __repr__(self):
        return f'<Semestre {self.numero} — {self.annee_scolaire_id}>'

    @property
    def label(self):
        return f'Semestre {self.numero}'

    @staticmethod
    def get_active():
        return Semestre.query.filter_by(est_actif=True).first()


class Niveau(db.Model):
    __tablename__ = 'niveaux'

    id          = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    nom         = db.Column(db.String(100),  nullable=False)
    nom_ar      = db.Column(db.String(100),  nullable=True)
    nom_en      = db.Column(db.String(100),  nullable=True)
    ordre       = db.Column(db.SmallInteger, nullable=False, unique=True)
    description = db.Column(db.Text,         nullable=True)
    est_actif   = db.Column(db.Boolean,      nullable=False,  default=True)
    created_at  = db.Column(db.DateTime,     default=lambda: datetime.now(timezone.utc))

    # Relationships
    sections    = db.relationship('Section',   back_populates='niveau',    lazy='dynamic')
    programmes  = db.relationship('Programme', back_populates='niveau',    lazy='dynamic')

    def __repr__(self):
        return f'<Niveau {self.ordre} — {self.nom}>'


class Specialite(db.Model):
    __tablename__ = 'specialites'

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

    # Relationships
    sections            = db.relationship('Section',        back_populates='specialite',    lazy='dynamic')
    programmes          = db.relationship('Programme',      back_populates='specialite',    lazy='dynamic')
    pdfs_emplois_temps  = db.relationship('PdfEmploiTemps', back_populates='specialite',    lazy='dynamic')

    def __repr__(self):
        return f'<Specialite {self.code} — {self.nom}>'


class Section(db.Model):
    __tablename__ = 'sections'

    id                = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    code_section      = db.Column(db.String(10),   nullable=False)
    specialite_id     = db.Column(db.Integer,      db.ForeignKey('specialites.id',     ondelete='RESTRICT'), nullable=False)
    niveau_id         = db.Column(db.Integer,      db.ForeignKey('niveaux.id',         ondelete='RESTRICT'), nullable=False)
    annee_scolaire_id = db.Column(db.Integer,      db.ForeignKey('annees_scolaires.id', ondelete='RESTRICT'), nullable=False)
    capacite_max      = db.Column(db.SmallInteger, nullable=False,   default=35)
    est_active        = db.Column(db.Boolean,      nullable=False,   default=True)
    created_at        = db.Column(db.DateTime,     default=lambda: datetime.now(timezone.utc))

    # Relationships
    specialite         = db.relationship('Specialite',      back_populates='sections')
    niveau             = db.relationship('Niveau',           back_populates='sections')
    annee_scolaire     = db.relationship('AnneeScolaire',   back_populates='sections')
    inscriptions       = db.relationship('Inscription',      back_populates='section',         lazy='dynamic')
    affectations       = db.relationship('AffectationEnseignement', back_populates='section',  lazy='dynamic')
    emploi_du_temps    = db.relationship('EmploiDuTemps',    back_populates='section',         lazy='dynamic')
    calendrier_examens = db.relationship('CalendrierExamen', back_populates='section',         lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('specialite_id', 'niveau_id', 'annee_scolaire_id', 'code_section',
                            name='uk_section'),
    )

    def __repr__(self):
        return f'<Section {self.code_section} — spe={self.specialite_id}>'

    @property
    def label(self):
        """Human-readable label: e.g. M1 AI — Groupe A"""
        return f'{self.niveau.nom} {self.specialite.code} — {self.code_section}'
