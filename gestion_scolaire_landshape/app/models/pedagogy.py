# =============================================================
#  EduNova — models/pedagogy.py
#  Cours, CoursConsulte, Devoir, SoumissionDevoir,
#  PostProfesseur, CommentairePost
# =============================================================
from datetime import datetime, timezone
from app.extensions import db


class Cours(db.Model):
    __tablename__ = 'cours'

    id                   = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    affectation_id       = db.Column(db.Integer,    db.ForeignKey('affectations_enseignement.id', ondelete='RESTRICT'), nullable=False)
    titre                = db.Column(db.String(255), nullable=False)
    description          = db.Column(db.Text,        nullable=True)
    type_contenu         = db.Column(db.Enum('pdf','image','video','audio','lien_externe'), nullable=False)
    fichier_url          = db.Column(db.String(500), nullable=True)
    nom_fichier_original = db.Column(db.String(255), nullable=True)
    taille_fichier_ko    = db.Column(db.BigInteger,  nullable=True)
    ordre                = db.Column(db.SmallInteger, nullable=False, default=0)
    est_publie           = db.Column(db.Boolean,     nullable=False, default=False)
    date_publication     = db.Column(db.DateTime,    nullable=True)
    publie_par           = db.Column(db.Integer,     db.ForeignKey('professeurs.id', ondelete='RESTRICT'), nullable=False)
    created_at           = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))
    updated_at           = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc),
                                      onupdate=lambda: datetime.now(timezone.utc))

    affectation      = db.relationship('AffectationEnseignement', back_populates='cours')
    professeur       = db.relationship('Professeur', foreign_keys=[publie_par])
    consultations    = db.relationship('CoursConsulte', back_populates='cours',
                                       lazy='dynamic', cascade='all, delete-orphan')
    conversations    = db.relationship('Conversation', back_populates='cours',
                                       foreign_keys='Conversation.cours_id', lazy='dynamic')

    def __repr__(self):
        return f'<Cours {self.titre[:40]}>'


class CoursConsulte(db.Model):
    __tablename__ = 'cours_consultes'

    id                         = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    cours_id                   = db.Column(db.Integer,  db.ForeignKey('cours.id',     ondelete='CASCADE'), nullable=False)
    etudiant_id                = db.Column(db.Integer,  db.ForeignKey('etudiants.id', ondelete='CASCADE'), nullable=False)
    date_premiere_consultation = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    date_derniere_consultation = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                           onupdate=lambda: datetime.now(timezone.utc))
    nombre_consultations       = db.Column(db.Integer,  nullable=False, default=1)

    cours    = db.relationship('Cours',    back_populates='consultations')
    etudiant = db.relationship('Etudiant', back_populates='cours_consultes')

    __table_args__ = (
        db.UniqueConstraint('cours_id', 'etudiant_id', name='uk_consultation'),
    )


class Devoir(db.Model):
    __tablename__ = 'devoirs'

    id                      = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    affectation_id          = db.Column(db.Integer,    db.ForeignKey('affectations_enseignement.id', ondelete='RESTRICT'), nullable=False)
    titre                   = db.Column(db.String(255), nullable=False)
    description             = db.Column(db.Text,        nullable=False)
    fichier_url             = db.Column(db.String(500), nullable=True)
    type_fichier            = db.Column(db.Enum('pdf','image','word','autre'), nullable=True)
    nom_fichier_original    = db.Column(db.String(255), nullable=True)
    date_publication        = db.Column(db.DateTime,    nullable=False)
    date_limite_soumission  = db.Column(db.DateTime,    nullable=False)
    note_maximale           = db.Column(db.Numeric(5,2), nullable=False, default=20.0)
    est_publie              = db.Column(db.Boolean,     nullable=False, default=False)
    publie_par              = db.Column(db.Integer,     db.ForeignKey('professeurs.id', ondelete='RESTRICT'), nullable=False)
    created_at              = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))
    updated_at              = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc),
                                         onupdate=lambda: datetime.now(timezone.utc))

    affectation  = db.relationship('AffectationEnseignement', back_populates='devoirs')
    professeur   = db.relationship('Professeur', foreign_keys=[publie_par])
    soumissions  = db.relationship('SoumissionDevoir', back_populates='devoir',
                                   lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Devoir {self.titre[:40]}>'


class SoumissionDevoir(db.Model):
    __tablename__ = 'soumissions_devoirs'

    id                   = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    devoir_id            = db.Column(db.Integer,    db.ForeignKey('devoirs.id',    ondelete='RESTRICT'), nullable=False)
    etudiant_id          = db.Column(db.Integer,    db.ForeignKey('etudiants.id',  ondelete='RESTRICT'), nullable=False)
    fichier_url          = db.Column(db.String(500), nullable=False)
    type_fichier         = db.Column(db.Enum('pdf','word','image','autre'), nullable=False)
    nom_fichier_original = db.Column(db.String(255), nullable=True)
    taille_fichier_ko    = db.Column(db.BigInteger,  nullable=True)
    date_soumission      = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))
    est_en_retard        = db.Column(db.Boolean,     nullable=False, default=False)
    note                 = db.Column(db.Numeric(5,2), nullable=True)
    commentaire_prof     = db.Column(db.Text,         nullable=True)
    date_correction      = db.Column(db.DateTime,     nullable=True)
    corrige_par          = db.Column(db.Integer,      db.ForeignKey('professeurs.id', ondelete='SET NULL'), nullable=True)

    devoir   = db.relationship('Devoir',    back_populates='soumissions')
    etudiant = db.relationship('Etudiant',  back_populates='soumissions')
    correcteur = db.relationship('Professeur', foreign_keys=[corrige_par])

    __table_args__ = (
        db.UniqueConstraint('devoir_id', 'etudiant_id', name='uk_soumission'),
    )

    def __repr__(self):
        return f'<SoumissionDevoir dev={self.devoir_id} etu={self.etudiant_id}>'


class PostProfesseur(db.Model):
    __tablename__ = 'posts_professeur'

    id             = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    professeur_id  = db.Column(db.Integer,  db.ForeignKey('professeurs.id',               ondelete='CASCADE'), nullable=False)
    affectation_id = db.Column(db.Integer,  db.ForeignKey('affectations_enseignement.id', ondelete='SET NULL'), nullable=True)
    contenu        = db.Column(db.Text,     nullable=False)
    type_public    = db.Column(db.Enum('section','tous'), nullable=False, default='tous')
    est_publie     = db.Column(db.Boolean,  nullable=False, default=True)
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                onupdate=lambda: datetime.now(timezone.utc))

    professeur   = db.relationship('Professeur',               back_populates='posts')
    affectation  = db.relationship('AffectationEnseignement',  back_populates='posts')
    commentaires = db.relationship('CommentairePost',           back_populates='post',
                                   lazy='dynamic', cascade='all, delete-orphan',
                                   order_by='CommentairePost.created_at')

    def __repr__(self):
        return f'<PostProfesseur prof={self.professeur_id} type={self.type_public}>'


class CommentairePost(db.Model):
    __tablename__ = 'commentaires_posts'

    id          = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    post_id     = db.Column(db.Integer,  db.ForeignKey('posts_professeur.id', ondelete='CASCADE'), nullable=False)
    auteur_id   = db.Column(db.Integer,  nullable=False)
    auteur_role = db.Column(db.Enum('etudiant','professeur'), nullable=False)
    contenu     = db.Column(db.Text,     nullable=False)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    post = db.relationship('PostProfesseur', back_populates='commentaires')

    def __repr__(self):
        return f'<CommentairePost post={self.post_id} auteur={self.auteur_id}>'
