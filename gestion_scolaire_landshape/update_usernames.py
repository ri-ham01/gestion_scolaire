from app import create_app, db
from app.models.user import Utilisateur
from app.models.profiles import Etudiant
from app.models.program import Inscription
from app.utils.helpers import generer_password_securise
import re

app = create_app()
app.app_context().push()

users = Utilisateur.query.filter_by(role='etudiant').all()

for u in users:
    etu = Etudiant.query.filter_by(utilisateur_id=u.id).first()
    if not etu:
        continue
    insc = Inscription.query.filter_by(etudiant_id=etu.id).first()
    if not insc:
        continue
        
    code_sec = insc.section.code_section.upper()
    suffix = 'A'
    if code_sec.endswith('B') or code_sec.endswith('2'):
        suffix = 'B'
    elif code_sec.endswith('C') or code_sec.endswith('3'):
        suffix = 'C'
        
    specialite = insc.section.specialite.code.lower()
    
    # Check if we need to update
    if not re.match(rf'^26{specialite}[A-Z]_\d+$', u.username):
        # Generate new username manually
        # E.g., from 26math01 -> 26mathA_1
        # Let's just use the logic from generer_username_etudiant but simple
        yy = str(insc.annee_scolaire.annee_debut)[-2:]
        prefix = f'{yy}{specialite}{suffix}'
        pattern = f'{prefix}%'
        
        existing = db.session.query(Utilisateur).filter(
            Utilisateur.role == 'etudiant',
            Utilisateur.username.like(pattern),
            Utilisateur.id != u.id
        ).all()
        
        max_num = 0
        for ex in existing:
            m = re.match(rf'^{re.escape(prefix)}_(\d+)$', ex.username)
            if m:
                max_num = max(max_num, int(m.group(1)))
        
        num = max_num + 1
        new_username = f'{prefix}_{num}'
        print(f"Updating {u.username} -> {new_username}")
        u.username = new_username
        
db.session.commit()
print("Updated all student usernames to new format.")
