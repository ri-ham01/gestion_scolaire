# =============================================================
#  EduNova — models/user.py
#  Table centrale d'authentification + UserMixin Flask-Login
# =============================================================
from datetime import datetime, timezone
from flask_login import UserMixin
from app.extensions import db, login_manager


class Utilisateur(UserMixin, db.Model):
    __tablename__ = 'utilisateurs'

    id                     = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    username               = db.Column(db.String(100),  nullable=False,   unique=True)
    password_hash          = db.Column(db.String(255),  nullable=False)
    email                  = db.Column(db.String(191),  unique=True,      nullable=True)
    role                   = db.Column(db.Enum('etudiant', 'professeur', 'parent', 'admin'), nullable=False)
    preference_langue      = db.Column(db.Enum('ar', 'fr', 'en'), nullable=False, default='fr')
    est_actif              = db.Column(db.Boolean,      nullable=False,   default=True)
    derniere_connexion     = db.Column(db.DateTime,     nullable=True)
    token_reinitialisation = db.Column(db.String(255),  nullable=True)
    token_expiration       = db.Column(db.DateTime,     nullable=True)
    email_verifie          = db.Column(db.Boolean,      nullable=False,   default=False)
    tentatives_connexion   = db.Column(db.SmallInteger, nullable=False,   default=0)
    compte_bloque_jusqu    = db.Column(db.DateTime,     nullable=True)
    created_at             = db.Column(db.DateTime,     default=lambda: datetime.now(timezone.utc))
    updated_at             = db.Column(db.DateTime,     default=lambda: datetime.now(timezone.utc),
                                       onupdate=lambda: datetime.now(timezone.utc))

    # ── Relationships (back refs) ──────────────────────────────
    administrateur  = db.relationship('Administrateur', back_populates='utilisateur', uselist=False)
    professeur      = db.relationship('Professeur',     back_populates='utilisateur', uselist=False)
    etudiant        = db.relationship('Etudiant',       back_populates='utilisateur', uselist=False)
    parent          = db.relationship('Parent',         back_populates='utilisateur', uselist=False)
    notifications   = db.relationship('Notification',  back_populates='destinataire',
                                      foreign_keys='Notification.destinataire_id',
                                      lazy='dynamic')
    push_tokens     = db.relationship('PushToken',      back_populates='utilisateur',   lazy='dynamic')
    statut_connexion = db.relationship('StatutConnexion', back_populates='utilisateur', uselist=False)

    def __repr__(self):
        return f'<Utilisateur {self.username} ({self.role})>'

    # ── Flask-Login helpers ───────────────────────────────────
    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self.est_actif

    # ── Password helpers (read-only hash) ─────────────────────
    @property
    def password(self):
        raise AttributeError('Le mot de passe n\'est pas lisible.')

    # NOTE: passwords are set ONLY by admin via bcrypt — no user change allowed
    def set_password(self, raw_password: str):
        from app.extensions import bcrypt
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode('utf-8')

    def check_password(self, raw_password: str) -> bool:
        from app.extensions import bcrypt
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    def update_last_login(self):
        self.derniere_connexion = datetime.now(timezone.utc)
        self.tentatives_connexion = 0
        self.compte_bloque_jusqu = None

    def increment_failed_login(self, max_attempts: int = 5):
        """Increment failed login attempts; lock account after max_attempts."""
        from datetime import timedelta
        self.tentatives_connexion += 1
        if self.tentatives_connexion >= max_attempts:
            self.compte_bloque_jusqu = datetime.now(timezone.utc) + timedelta(minutes=15)

    @property
    def is_locked(self) -> bool:
        if self.compte_bloque_jusqu is None:
            return False
        now = datetime.now(timezone.utc)
        if self.compte_bloque_jusqu.tzinfo is None:
            # naive datetime stored in DB — compare without tz
            from datetime import datetime as dt
            return dt.utcnow() < self.compte_bloque_jusqu
        return now < self.compte_bloque_jusqu

    # ── Role helpers ──────────────────────────────────────────
    @property
    def is_admin(self)       -> bool: return self.role == 'admin'
    @property
    def is_professeur(self)  -> bool: return self.role == 'professeur'
    @property
    def is_etudiant(self)    -> bool: return self.role == 'etudiant'
    @property
    def is_parent(self)      -> bool: return self.role == 'parent'


# ── Flask-Login user loader ────────────────────────────────
@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(Utilisateur, int(user_id))
