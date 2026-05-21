# =============================================================
#  EduNova — models/communication.py
#  Notification, Conversation, Message, MessageAccuseReception,
#  Annonce, AnnonceFichier, PushToken, StatutConnexion,
#  FileNotificationExterne
# =============================================================
from datetime import datetime, timezone
from app.extensions import db


class Notification(db.Model):
    __tablename__ = 'notifications'

    id                = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    type              = db.Column(db.Enum(
                            'absence_enregistree','absence_justifiee','absence_refusee',
                            'seuil_absences_atteint','exclusion_absences',
                            'note_publiee','devoir_publie','cours_publie',
                            'correction_publiee','message_recu','annonce',
                            'post_publie','commentaire_recu','releve_disponible',
                            'mot_de_passe_envoye','autre'), nullable=False)
    destinataire_id   = db.Column(db.Integer,  db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False)
    destinataire_role = db.Column(db.Enum('etudiant','professeur','parent','admin'), nullable=False)
    titre             = db.Column(db.String(255), nullable=False)
    contenu           = db.Column(db.Text,        nullable=False)
    est_lu            = db.Column(db.Boolean,     nullable=False, default=False)
    date_lecture      = db.Column(db.DateTime,    nullable=True)
    reference_table   = db.Column(db.String(50),  nullable=True)
    reference_id      = db.Column(db.Integer,     nullable=True)
    date_envoi        = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))

    destinataire = db.relationship('Utilisateur', back_populates='notifications')

    def __repr__(self):
        return f'<Notification type={self.type} dest={self.destinataire_id}>'

    def marquer_lu(self):
        self.est_lu      = True
        self.date_lecture = datetime.now(timezone.utc)
        db.session.add(self)


class Conversation(db.Model):
    __tablename__ = 'conversations'

    id                    = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    type                  = db.Column(db.Enum('etudiant_professeur','parent_professeur',
                                               'cours_etudiant_professeur'), nullable=False)
    participant_a_id      = db.Column(db.Integer,  nullable=False)
    participant_a_role    = db.Column(db.Enum('etudiant','parent'), nullable=False)
    participant_b_id      = db.Column(db.Integer,  nullable=False)  # toujours professeur
    sujet                 = db.Column(db.String(255), nullable=True)
    matiere_id            = db.Column(db.Integer,  db.ForeignKey('matieres.id',   ondelete='SET NULL'), nullable=True)
    etudiant_concerne_id  = db.Column(db.Integer,  db.ForeignKey('etudiants.id',  ondelete='SET NULL'), nullable=True)
    cours_id              = db.Column(db.Integer,  db.ForeignKey('cours.id',      ondelete='SET NULL'), nullable=True)
    est_active            = db.Column(db.Boolean,  nullable=False, default=True)
    date_creation         = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    date_dernier_message  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                      onupdate=lambda: datetime.now(timezone.utc))

    matiere              = db.relationship('Matiere',   back_populates='conversations')
    etudiant_concerne    = db.relationship('Etudiant',  foreign_keys=[etudiant_concerne_id])
    cours                = db.relationship('Cours',     foreign_keys=[cours_id])
    messages             = db.relationship('Message',   back_populates='conversation',
                                           lazy='dynamic', order_by='Message.date_envoi')

    def __repr__(self):
        return f'<Conversation {self.type} a={self.participant_a_id} b={self.participant_b_id}>'

    def get_non_lus_pour(self, utilisateur_id: int) -> int:
        return self.messages.filter(
            Message.expediteur_utilisateur_id != utilisateur_id,
            Message.est_lu == False  # noqa
        ).count()


class Message(db.Model):
    __tablename__ = 'messages'

    id                        = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    conversation_id           = db.Column(db.Integer,  db.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)
    expediteur_utilisateur_id = db.Column(db.Integer,  nullable=False)
    expediteur_role           = db.Column(db.Enum('etudiant','professeur','parent'), nullable=False)
    contenu                   = db.Column(db.Text,     nullable=False)
    fichier_url               = db.Column(db.String(500), nullable=True)
    type_fichier              = db.Column(db.Enum('pdf','image','audio','video','autre'), nullable=True)
    est_lu                    = db.Column(db.Boolean,  nullable=False, default=False)
    date_lecture              = db.Column(db.DateTime, nullable=True)
    date_envoi                = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    supprime_par_expediteur   = db.Column(db.Boolean,  nullable=False, default=False)
    supprime_par_destinataire = db.Column(db.Boolean,  nullable=False, default=False)

    conversation = db.relationship('Conversation', back_populates='messages')

    def __repr__(self):
        return f'<Message conv={self.conversation_id} de={self.expediteur_utilisateur_id}>'


class Annonce(db.Model):
    __tablename__ = 'annonces'

    id               = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    admin_id         = db.Column(db.Integer,  db.ForeignKey('administrateurs.id', ondelete='RESTRICT'), nullable=False)
    titre            = db.Column(db.String(255), nullable=False)
    contenu          = db.Column(db.Text,        nullable=False)
    public_cible     = db.Column(db.String(100), nullable=False, default='tous')
    est_publie       = db.Column(db.Boolean,     nullable=False, default=False)
    est_epinglee     = db.Column(db.Boolean,     nullable=False, default=False)
    date_publication = db.Column(db.DateTime,    nullable=True)
    date_expiration  = db.Column(db.DateTime,    nullable=True)
    created_at       = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))
    updated_at       = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc),
                                  onupdate=lambda: datetime.now(timezone.utc))

    admin    = db.relationship('Administrateur', back_populates='annonces')
    fichiers = db.relationship('AnnonceFichier', back_populates='annonce',
                               lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Annonce {self.titre[:30]}>'


class AnnonceFichier(db.Model):
    __tablename__ = 'annonces_fichiers'

    id           = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    annonce_id   = db.Column(db.Integer,  db.ForeignKey('annonces.id', ondelete='CASCADE'), nullable=False)
    fichier_url  = db.Column(db.String(500), nullable=False)
    nom_fichier  = db.Column(db.String(255), nullable=True)
    type_fichier = db.Column(db.Enum('pdf','image','word','video','autre'), nullable=True)

    annonce = db.relationship('Annonce', back_populates='fichiers')


class PushToken(db.Model):
    __tablename__ = 'push_tokens'

    id                        = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    utilisateur_id            = db.Column(db.Integer,  db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False)
    token                     = db.Column(db.String(512), nullable=False, unique=True)
    type_token                = db.Column(db.Enum('fcm','webpush','email'), nullable=False, default='webpush')
    appareil                  = db.Column(db.String(150), nullable=True)
    est_actif                 = db.Column(db.Boolean,  nullable=False, default=True)
    date_enregistrement       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    date_derniere_utilisation = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                          onupdate=lambda: datetime.now(timezone.utc))

    utilisateur = db.relationship('Utilisateur', back_populates='push_tokens')


class StatutConnexion(db.Model):
    __tablename__ = 'statut_connexion'

    utilisateur_id    = db.Column(db.Integer,  db.ForeignKey('utilisateurs.id', ondelete='CASCADE'),
                                  primary_key=True)
    est_en_ligne      = db.Column(db.Boolean,  nullable=False, default=False)
    derniere_activite = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                  onupdate=lambda: datetime.now(timezone.utc))
    socket_id         = db.Column(db.String(100), nullable=True)

    utilisateur = db.relationship('Utilisateur', back_populates='statut_connexion')


class FileNotificationExterne(db.Model):
    __tablename__ = 'file_notifications_externes'

    id                  = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    utilisateur_id      = db.Column(db.Integer,    db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False)
    canal               = db.Column(db.Enum('push','email','push_et_email'), nullable=False, default='push')
    titre               = db.Column(db.String(255), nullable=False)
    corps               = db.Column(db.Text,         nullable=False)
    url_action          = db.Column(db.String(500),  nullable=True)
    declencheur         = db.Column(db.String(60),   nullable=False, default='autre')
    reference_table     = db.Column(db.String(60),   nullable=True)
    reference_id        = db.Column(db.BigInteger,   nullable=True)
    statut              = db.Column(db.Enum('en_attente','envoyee','echec','ignoree'),
                                    nullable=False, default='en_attente')
    tentatives          = db.Column(db.SmallInteger, nullable=False, default=0)
    derniere_tentative  = db.Column(db.DateTime,     nullable=True)
    erreur_detail       = db.Column(db.Text,         nullable=True)
    created_at          = db.Column(db.DateTime,     default=lambda: datetime.now(timezone.utc))
    traitee_le          = db.Column(db.DateTime,     nullable=True)
