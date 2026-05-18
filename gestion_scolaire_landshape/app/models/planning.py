# =============================================================
#  EduNova — models/planning.py
#  CalendrierExamen, EmploiDuTemps, PdfEmploiTemps
# =============================================================
from datetime import datetime, timezone
from app.extensions import db


class CalendrierExamen(db.Model):
    __tablename__ = 'calendrier_examens'

    id           = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    section_id   = db.Column(db.Integer,  db.ForeignKey('sections.id',                  ondelete='RESTRICT'), nullable=False)
    matiere_id   = db.Column(db.Integer,  db.ForeignKey('matieres.id',                  ondelete='RESTRICT'), nullable=False)
    semestre_id  = db.Column(db.Integer,  db.ForeignKey('semestres.id',                 ondelete='RESTRICT'), nullable=False)
    affectation_id = db.Column(db.Integer, db.ForeignKey('affectations_enseignement.id', ondelete='RESTRICT'), nullable=True)
    type_examen  = db.Column(db.Enum('devoir1','devoir2','examen','rattrapage','evaluation_continue'), nullable=False)
    date_examen  = db.Column(db.Date,     nullable=False)
    heure_debut  = db.Column(db.Time,     nullable=False)
    heure_fin    = db.Column(db.Time,     nullable=False)
    salle        = db.Column(db.String(100), nullable=True)
    surveillants = db.Column(db.Text,     nullable=True)   # JSON list
    est_publie   = db.Column(db.Boolean,  nullable=False, default=False)
    publie_par   = db.Column(db.Integer,  db.ForeignKey('administrateurs.id', ondelete='RESTRICT'), nullable=False)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))

    section     = db.relationship('Section',    back_populates='calendrier_examens')
    matiere     = db.relationship('Matiere',    foreign_keys=[matiere_id])
    semestre    = db.relationship('Semestre',   back_populates='calendrier_examens')
    affectation = db.relationship('AffectationEnseignement', back_populates='calendrier_examens')
    admin       = db.relationship('Administrateur', foreign_keys=[publie_par])

    def __repr__(self):
        return f'<CalendrierExamen sec={self.section_id} mat={self.matiere_id} date={self.date_examen}>'


class EmploiDuTemps(db.Model):
    __tablename__ = 'emploi_du_temps'

    id             = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    section_id     = db.Column(db.Integer,     db.ForeignKey('sections.id',                  ondelete='RESTRICT'), nullable=False)
    affectation_id = db.Column(db.Integer,     db.ForeignKey('affectations_enseignement.id', ondelete='RESTRICT'), nullable=False)
    semestre_id    = db.Column(db.Integer,     db.ForeignKey('semestres.id',                 ondelete='RESTRICT'), nullable=False)
    jour_semaine   = db.Column(db.SmallInteger, nullable=False)   # 0=Dim…6=Sam
    heure_debut    = db.Column(db.Time,         nullable=False)
    heure_fin      = db.Column(db.Time,         nullable=False)
    salle          = db.Column(db.String(100),  nullable=True)
    type_seance    = db.Column(db.Enum('cours','td','tp'), nullable=False, default='cours')
    est_actif      = db.Column(db.Boolean,      nullable=False, default=True)
    publie_par     = db.Column(db.Integer,      db.ForeignKey('administrateurs.id', ondelete='SET NULL'), nullable=True)
    created_at     = db.Column(db.DateTime,     default=lambda: datetime.now(timezone.utc))
    updated_at     = db.Column(db.DateTime,     default=lambda: datetime.now(timezone.utc),
                                onupdate=lambda: datetime.now(timezone.utc))

    section     = db.relationship('Section',     back_populates='emploi_du_temps')
    affectation = db.relationship('AffectationEnseignement', back_populates='emploi_du_temps')
    semestre    = db.relationship('Semestre',    back_populates='emploi_du_temps')
    admin       = db.relationship('Administrateur', foreign_keys=[publie_par])

    JOURS_FR = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
    JOURS_AR = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']

    @property
    def jour_label_fr(self):
        return self.JOURS_FR[self.jour_semaine] if 0 <= self.jour_semaine <= 6 else '?'

    @property
    def jour_label_ar(self):
        return self.JOURS_AR[self.jour_semaine] if 0 <= self.jour_semaine <= 6 else '?'

    def __repr__(self):
        return f'<EmploiDuTemps sec={self.section_id} jour={self.jour_semaine}>'


class PdfEmploiTemps(db.Model):
    """Cache des PDFs générés des emplois du temps et examens."""
    __tablename__ = 'pdfs_emplois_temps'

    id                = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    specialite_id     = db.Column(db.Integer,     db.ForeignKey('specialites.id',      ondelete='CASCADE'), nullable=False)
    semestre_id       = db.Column(db.Integer,     db.ForeignKey('semestres.id',        ondelete='CASCADE'), nullable=False)
    type_pdf          = db.Column(db.Enum('hebdomadaire','examens'), nullable=False)
    fichier_url       = db.Column(db.String(500), nullable=False)
    nom_fichier       = db.Column(db.String(255), nullable=False)
    taille_fichier_ko = db.Column(db.Integer,     nullable=True)
    genere_par        = db.Column(db.Integer,     db.ForeignKey('administrateurs.id', ondelete='RESTRICT'), nullable=False)
    created_at        = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))
    updated_at        = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc),
                                   onupdate=lambda: datetime.now(timezone.utc))

    specialite = db.relationship('Specialite', back_populates='pdfs_emplois_temps')
    semestre   = db.relationship('Semestre',   back_populates='pdfs_emplois_temps')
    admin      = db.relationship('Administrateur', foreign_keys=[genere_par])

    __table_args__ = (
        db.UniqueConstraint('specialite_id', 'semestre_id', 'type_pdf', name='uk_pdf_edt'),
    )

    def __repr__(self):
        return f'<PdfEmploiTemps spe={self.specialite_id} type={self.type_pdf}>'
