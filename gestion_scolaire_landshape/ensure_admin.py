from app import create_app
from app.extensions import db
from app.models.user import Utilisateur
from app.models.profiles import Administrateur

app = create_app()

with app.app_context():
    # Check if admin exists
    admin = Utilisateur.query.filter_by(username='admin').first()
    if not admin:
        print("Admin user 'admin' not found. Creating...")
        admin = Utilisateur(
            username='admin',
            email='admin@edunova.dz',
            role='admin',
            est_actif=True,
            email_verifie=True
        )
        admin.set_password('1234')
        db.session.add(admin)
        db.session.flush() # to get admin.id
        
        admin_profile = Administrateur(
            utilisateur_id=admin.id,
            nom='Admin',
            prenom='Super',
            telephone='+213 00 00 00 00'
        )
        db.session.add(admin_profile)
        db.session.commit()
        print("Admin user created successfully (username: 'admin', password: '1234').")
    else:
        print("Admin user exists. Updating password to '1234'...")
        admin.set_password('1234')
        admin.est_actif = True
        db.session.commit()
        print("Admin user updated successfully (password: '1234').")
