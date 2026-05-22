from app import create_app, db
from app.models.profiles import Etudiant
from app.models.program import Inscription

app = create_app()
app.app_context().push()

students = Etudiant.query.all()
for e in students:
    if e.utilisateur.username.startswith('26math') or e.utilisateur.username.startswith('26info'):
        insc = Inscription.query.filter_by(etudiant_id=e.id).first()
        section = insc.section.code_section if insc else "None"
        pwd = "password123" # assuming all reset or using old logic
        print(f"User: {e.utilisateur.username} | Password: {pwd} | Nom: {e.prenom} {e.nom} | Section: {section}")
