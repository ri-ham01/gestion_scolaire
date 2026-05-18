# =============================================================
#  EduNova — models/presence.py
#  Seance, Presence, CompteurAbsences
# =============================================================
from datetime import datetime, timezone
from app.extensions import db


class Seance(db.Model):
    __tablename__ = 'seances'

    id               = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    affectation_id   = db.Column(db.Integer,  db.ForeignKey('affectations_enseignement.id', ondelete='RESTRICT'), nullable=False)
    date_seance      = db.Column(db.Date,     nullable=False)
    heure_debut      = db.Column(db.Time,     nullable=False)
    heure_fin        = db.Column(db.Time,     nullable=False)
    type_seance      = db.Column(db.Enum('cours','td','tp','examen','rattrapage'), nullable=False, default='cours')
    salle            = db.Column(db.String(50), nullable=True)
    est_annulee      = db.Column(db.Boolean,  nullable=False, default=False)
    motif_annulation = db.Column(db.String(255), nullable=True)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    affectation = db.relationship('AffectationEnseignement', back_populates='seances')
    presences   = db.relationship('Presence', back_populates='seance', lazy='dynamic',
                                  cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Seance aff={self.affectation_id} date={self.date_seance}>'


class Presence(db.Model):
    __tablename__ = 'presences'

    id                     = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    seance_id              = db.Column(db.Integer,  db.ForeignKey('seances.id',         ondelete='RESTRICT'), nullable=False)
    etudiant_id            = db.Column(db.Integer,  db.ForeignKey('etudiants.id',       ondelete='RESTRICT'), nullable=False)
    statut                 = db.Column(db.Enum('present','absent','retard','excuse'),     nullable=False, default='present')
    justification          = db.Column(db.Text,     nullable=True)
    fichier_justification  = db.Column(db.String(500), nullable=True)
    justifie_par_parent_id = db.Column(db.Integer,  db.ForeignKey('parents.id',         ondelete='SET NULL'), nullable=True)
    date_justification     = db.Column(db.DateTime, nullable=True)
    statut_justification   = db.Column(db.Enum('en_attente','acceptee','refusee'),       nullable=True)
    traite_par_admin_id    = db.Column(db.Integer,  db.ForeignKey('administrateurs.id', ondelete='SET NULL'), nullable=True)
    date_traitement        = db.Column(db.DateTime, nullable=True)
    enregistre_par         = db.Column(db.Integer,  db.ForeignKey('professeurs.id',     ondelete='RESTRICT'), nullable=False)
    date_enregistrement    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    seance                  = db.relationship('Seance',         back_populates='presences')
    etudiant                = db.relationship('Etudiant',       back_populates='presences')
    parent_justificateur    = db.relationship('Parent',         foreign_keys=[justifie_par_parent_id])
    professeur_enregistreur = db.relationship('Professeur',     foreign_keys=[enregistre_par])
    admin_traiteur          = db.relationship('Administrateur', foreign_keys=[traite_par_admin_id])

    __table_args__ = (
        db.UniqueConstraint('seance_id', 'etudiant_id', name='uk_presence'),
    )

    def __repr__(self):
        return f'<Presence etu={self.etudiant_id} statut={self.statut}>'

    def accepter_justification(self, admin_id: int):
        self.statut_justification = 'acceptee'
        self.traite_par_admin_id  = admin_id
        self.date_traitement      = datetime.now(timezone.utc)
        self.statut               = 'excuse'
        db.session.add(self)

    def refuser_justification(self, admin_id: int):
        self.statut_justification = 'refusee'
        self.traite_par_admin_id  = admin_id
        self.date_traitement      = datetime.now(timezone.utc)
        db.session.add(self)


class CompteurAbsences(db.Model):
    __tablename__ = 'compteur_absences'

    id                      = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    etudiant_id             = db.Column(db.Integer,  db.ForeignKey('etudiants.id',    ondelete='RESTRICT'), nullable=False)
    inscription_id          = db.Column(db.Integer,  db.ForeignKey('inscriptions.id', ondelete='RESTRICT'), nullable=False)
    semestre_id             = db.Column(db.Integer,  db.ForeignKey('semestres.id',    ondelete='RESTRICT'), nullable=False)
    total_seances           = db.Column(db.Integer,  nullable=False, default=0)
    total_absences          = db.Column(db.Integer,  nullable=False, default=0)
    absences_justifiees     = db.Column(db.Integer,  nullable=False, default=0)
    absences_non_justifiees = db.Column(db.Integer,  nullable=False, default=0)
    est_exclu               = db.Column(db.Boolean,  nullable=False, default=False)
    date_exclusion          = db.Column(db.DateTime, nullable=True)
    updated_at              = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                        onupdate=lambda: datetime.now(timezone.utc))

    etudiant    = db.relationship('Etudiant',    foreign_keys=[etudiant_id])
    inscription = db.relationship('Inscription', back_populates='compteur_absences')
    semestre    = db.relationship('Semestre',    foreign_keys=[semestre_id])

    __table_args__ = (
        db.UniqueConstraint('etudiant_id', 'inscription_id', 'semestre_id', name='uk_compteur'),
    )

    def incrementer_absence(self, justifiee: bool = False):
        from app.utils.helpers import get_param_int
        seuil = get_param_int('seuil_exclusion_absences', 10)
        self.total_absences += 1
        if justifiee:
            self.absences_justifiees += 1
        else:
            self.absences_non_justifiees += 1
            if self.absences_non_justifiees >= seuil and not self.est_exclu:
                self.est_exclu      = True
                self.date_exclusion = datetime.now(timezone.utc)
                self.inscription.statut = 'exclu'
                db.session.add(self.inscription)
        db.session.add(self)
