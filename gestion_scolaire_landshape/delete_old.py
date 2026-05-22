from app import create_app, db
from app.models.user import Utilisateur
from app.models.profiles import Etudiant, ParentEtudiant
from app.models.program import Inscription
from app.models.evaluation import Note, ResultatSemestre, ResultatAnnuel

app = create_app()
app.app_context().push()

users = Utilisateur.query.filter_by(role='etudiant').all()
count = 0
for u in users:
    if u.username.startswith('math') or u.username.startswith('info') or u.username.startswith('etu_'):
        etu = Etudiant.query.filter_by(utilisateur_id=u.id).first()
        if etu:
            # Delete dependent records
            ParentEtudiant.query.filter_by(etudiant_id=etu.id).delete()
            Inscription.query.filter_by(etudiant_id=etu.id).delete()
            Note.query.filter_by(etudiant_id=etu.id).delete()
            ResultatSemestre.query.filter_by(etudiant_id=etu.id).delete()
            ResultatAnnuel.query.filter_by(etudiant_id=etu.id).delete()
            db.session.delete(etu)
        db.session.delete(u)
        count += 1

db.session.commit()
print(f'Deleted {count} old students')
