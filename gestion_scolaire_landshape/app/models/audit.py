# =============================================================
#  EduNova — models/audit.py
#  JournalConnexion, JournalAdmin
# =============================================================
from datetime import datetime, timezone
from app.extensions import db


class JournalConnexion(db.Model):
    __tablename__ = 'journal_connexions'

    id             = db.Column(db.BigInteger,  primary_key=True, autoincrement=True)
    utilisateur_id = db.Column(db.Integer,     nullable=False)
    adresse_ip     = db.Column(db.String(45),  nullable=True)
    user_agent     = db.Column(db.String(500), nullable=True)
    statut         = db.Column(db.Enum('succes','echec','bloque'), nullable=False, default='succes')
    date_connexion = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<JournalConnexion usr={self.utilisateur_id} statut={self.statut}>'


class JournalAdmin(db.Model):
    __tablename__ = 'journal_admin'

    id                  = db.Column(db.BigInteger,  primary_key=True, autoincrement=True)
    admin_id            = db.Column(db.Integer,     db.ForeignKey('administrateurs.id', ondelete='RESTRICT'), nullable=False)
    action              = db.Column(db.String(100), nullable=False)
    table_affectee      = db.Column(db.String(100), nullable=True)
    enregistrement_id   = db.Column(db.Integer,     nullable=True)
    details_avant       = db.Column(db.JSON,        nullable=True)
    details_apres       = db.Column(db.JSON,        nullable=True)
    adresse_ip          = db.Column(db.String(45),  nullable=True)
    date_action         = db.Column(db.DateTime,    default=lambda: datetime.now(timezone.utc))

    admin = db.relationship('Administrateur', back_populates='journal_admin')

    def __repr__(self):
        return f'<JournalAdmin admin={self.admin_id} action={self.action}>'
