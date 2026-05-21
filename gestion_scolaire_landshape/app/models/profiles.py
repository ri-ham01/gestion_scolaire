# =============================================================
#  EduNova — models/profiles.py
#  Profils: Administrateur, Professeur, Etudiant, Parent,
#           ParentEtudiant, DemandeInscriptionParent
# =============================================================
from datetime import datetime, timezone
from app.extensions import db


class Administrateur(db.Model):
    __tablename__ = 'administrateurs'

    id             = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    utilisateur_id = db.Column(db.Integer,     db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False, unique=True)
    nom            = db.Column(db.String(100), nullable=False)
    prenom         = db.Column(db.String(100), nullable=False)
    telephone      = db.Column(db.String(20),  nullable=True)
    photo_url      = db.Column(db.String(500), nullable=True)
    created_at     = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))
    updated_at     = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc),
                                onupdate=lambda: datetime.now(timezone.utc))

    utilisateur  = db.relationship('Utilisateur',   back_populates='administrateur')
    annonces     = db.relationship('Annonce',        back_populates='admin',          lazy='dynamic')
    journal_admin = db.relationship('JournalAdmin',  back_populates='admin',          lazy='dynamic')

    def __repr__(self):
        return f'<Admin {self.prenom} {self.nom}>'

    @property
    def nom_complet(self):
        return f'{self.prenom} {self.nom}'


class Professeur(db.Model):
    __tablename__ = 'professeurs'

    id                    = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    utilisateur_id        = db.Column(db.Integer,     db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False, unique=True)
    matricule             = db.Column(db.String(50),  nullable=False,   unique=True)
    nom                   = db.Column(db.String(100), nullable=False)
    prenom                = db.Column(db.String(100), nullable=False)
    date_naissance        = db.Column(db.Date,        nullable=True)
    lieu_naissance        = db.Column(db.String(150), nullable=True)
    email_professionnel   = db.Column(db.String(191), nullable=True)
    telephone             = db.Column(db.String(20),  nullable=True)
    photo_url             = db.Column(db.String(500), nullable=True)
    date_recrutement      = db.Column(db.Date,        nullable=True)
    grade                 = db.Column(db.String(100), nullable=True)
    est_actif             = db.Column(db.Boolean,     nullable=False,   default=True)
    created_at            = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))
    updated_at            = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc),
                                       onupdate=lambda: datetime.now(timezone.utc))

    utilisateur  = db.relationship('Utilisateur',            back_populates='professeur')
    affectations = db.relationship('AffectationEnseignement', back_populates='professeur',    lazy='dynamic')
    notes_saisies = db.relationship('Note',                   back_populates='professeur_saisie',
                                    foreign_keys='Note.saisie_par', lazy='dynamic')
    seances      = db.relationship('Seance',
                                    primaryjoin='Seance.affectation_id == AffectationEnseignement.id',
                                    secondary='affectations_enseignement',
                                    secondaryjoin='AffectationEnseignement.professeur_id == Professeur.id',
                                    viewonly=True, lazy='dynamic')
    posts        = db.relationship('PostProfesseur',          back_populates='professeur',    lazy='dynamic')

    def __repr__(self):
        return f'<Professeur {self.prenom} {self.nom} — {self.matricule}>'

    @property
    def nom_complet(self):
        return f'{self.prenom} {self.nom}'


class Etudiant(db.Model):
    __tablename__ = 'etudiants'

    id             = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    utilisateur_id = db.Column(db.Integer,     db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False, unique=True)
    matricule      = db.Column(db.String(50),  nullable=False,   unique=True)
    nom            = db.Column(db.String(100), nullable=False)
    prenom         = db.Column(db.String(100), nullable=False)
    date_naissance = db.Column(db.Date,        nullable=True)
    sexe           = db.Column(db.Enum('M', 'F'), nullable=True)
    lieu_naissance = db.Column(db.String(150), nullable=True)
    adresse        = db.Column(db.Text,        nullable=True)
    telephone      = db.Column(db.String(20),  nullable=True)
    photo_url      = db.Column(db.String(500), nullable=True)
    est_actif      = db.Column(db.Boolean,     nullable=False,   default=True)
    created_at     = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))
    updated_at     = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc),
                                onupdate=lambda: datetime.now(timezone.utc))

    utilisateur    = db.relationship('Utilisateur',  back_populates='etudiant')
    inscriptions   = db.relationship('Inscription',  back_populates='etudiant', lazy='dynamic')
    notes          = db.relationship('Note',          back_populates='etudiant', lazy='dynamic')
    presences      = db.relationship('Presence',      back_populates='etudiant', lazy='dynamic')
    soumissions    = db.relationship('SoumissionDevoir', back_populates='etudiant', lazy='dynamic')
    cours_consultes = db.relationship('CoursConsulte', back_populates='etudiant', lazy='dynamic')
    parents_link   = db.relationship('ParentEtudiant', back_populates='etudiant', lazy='dynamic')

    def __repr__(self):
        return f'<Etudiant {self.prenom} {self.nom} — {self.matricule}>'

    @property
    def nom_complet(self):
        return f'{self.prenom} {self.nom}'

    def get_inscription_active(self):
        """Renvoie l'inscription active de l'étudiant pour l'année scolaire en cours."""
        from app.models.academic import AnneeScolaire
        annee = AnneeScolaire.get_active()
        if not annee:
            return None
        return self.inscriptions.filter_by(annee_scolaire_id=annee.id, statut='actif').first()


class Parent(db.Model):
    __tablename__ = 'parents'

    id                          = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    utilisateur_id              = db.Column(db.Integer,     db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False, unique=True)
    nom                         = db.Column(db.String(100), nullable=False)
    prenom                      = db.Column(db.String(100), nullable=False)
    email                       = db.Column(db.String(191), nullable=False,   unique=True)
    telephone                   = db.Column(db.String(20),  nullable=True)
    adresse                     = db.Column(db.Text,        nullable=True)
    profession                  = db.Column(db.String(150), nullable=True)
    statut_emploi               = db.Column(db.Enum('employe', 'sans_emploi', 'retraite', 'autre'), nullable=True)
    photo_url                   = db.Column(db.String(500), nullable=True)
    email_verifie               = db.Column(db.Boolean,     nullable=False,   default=False)
    token_verification_email    = db.Column(db.String(255), nullable=True)
    token_email_expiration      = db.Column(db.DateTime,    nullable=True)
    created_at                  = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))
    updated_at                  = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc),
                                             onupdate=lambda: datetime.now(timezone.utc))

    utilisateur  = db.relationship('Utilisateur',    back_populates='parent')
    enfants_link = db.relationship('ParentEtudiant', back_populates='parent',  lazy='dynamic')

    def __repr__(self):
        return f'<Parent {self.prenom} {self.nom}>'

    @property
    def nom_complet(self):
        return f'{self.prenom} {self.nom}'

    def get_enfants(self):
        return [link.etudiant for link in self.enfants_link.all()]


class ParentEtudiant(db.Model):
    """Table de liaison Parent ↔ Étudiant"""
    __tablename__ = 'parent_etudiant'

    id                          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    parent_id                   = db.Column(db.Integer, db.ForeignKey('parents.id',   ondelete='CASCADE'), nullable=False)
    etudiant_id                 = db.Column(db.Integer, db.ForeignKey('etudiants.id', ondelete='CASCADE'), nullable=False)
    lien                        = db.Column(db.Enum('pere', 'mere', 'tuteur', 'tutrice', 'autre'), nullable=False, default='tuteur')
    est_responsable_principal   = db.Column(db.Boolean, nullable=False, default=True)
    peut_consulter_notes        = db.Column(db.Boolean, nullable=False, default=True)
    peut_recevoir_notifications = db.Column(db.Boolean, nullable=False, default=True)

    parent   = db.relationship('Parent',   back_populates='enfants_link')
    etudiant = db.relationship('Etudiant', back_populates='parents_link')

    __table_args__ = (
        db.UniqueConstraint('parent_id', 'etudiant_id', name='uk_par_etu'),
    )

    def __repr__(self):
        return f'<ParentEtudiant {self.parent_id} ↔ {self.etudiant_id}>'


class DemandeInscriptionParent(db.Model):
    __tablename__ = 'demandes_inscription_parent'

    id                  = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    nom                 = db.Column(db.String(100), nullable=False)
    prenom              = db.Column(db.String(100), nullable=False)
    email               = db.Column(db.String(191), nullable=False, unique=True)
    telephone           = db.Column(db.String(20),  nullable=True)
    adresse             = db.Column(db.Text,        nullable=True)
    profession          = db.Column(db.String(150), nullable=True)
    lien_parente        = db.Column(db.Enum('pere', 'mere', 'tuteur', 'tutrice', 'autre'),
                                    nullable=False, default='tuteur')
    matricule_etudiant  = db.Column(db.String(50),  nullable=True)
    statut              = db.Column(db.Enum('en_attente', 'approuvee', 'rejetee'),
                                    nullable=False, default='en_attente')
    motif_rejet         = db.Column(db.Text,        nullable=True)
    traite_par          = db.Column(db.Integer,     db.ForeignKey('administrateurs.id', ondelete='SET NULL'), nullable=True)
    date_traitement     = db.Column(db.DateTime,    nullable=True)
    created_at          = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<DemandeInscriptionParent {self.email} — {self.statut}>'
