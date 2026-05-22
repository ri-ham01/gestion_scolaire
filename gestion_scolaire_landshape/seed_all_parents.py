import app
import string
import random
from app.models.profiles import Etudiant, Parent, ParentEtudiant
from app.models import Utilisateur
from werkzeug.security import generate_password_hash

a = app.create_app()
with a.app_context():
    from app import db
    etus = Etudiant.query.all()
    count = 0
    for e in etus:
        if e.parents_link.count() == 0:
            prenom_clean = e.prenom.lower().replace(' ', '').replace('é', 'e').replace('è', 'e').replace('â', 'a')
            nom_clean = e.nom.lower().replace(' ', '').replace('é', 'e').replace('è', 'e').replace('â', 'a')
            email = f"parent.{prenom_clean}.{nom_clean}@edu.nova.dz"
            
            # Create user
            u = Utilisateur(
                username=email,
                email=email,
                password_hash=generate_password_hash('12345'),
                role='parent'
            )
            db.session.add(u)
            db.session.flush()
            
            p = Parent(
                utilisateur_id=u.id,
                nom=e.nom,
                prenom='Parent de ' + e.prenom,
                email=email,
                telephone='0' + ''.join(random.choices(string.digits, k=9))
            )
            db.session.add(p)
            db.session.flush()
            
            pe = ParentEtudiant(parent_id=p.id, etudiant_id=e.id, lien='Père')
            db.session.add(pe)
            count += 1
    
    db.session.commit()
    print(f"{count} parents crees.")
