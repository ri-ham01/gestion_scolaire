from app import create_app
from app.extensions import db
from app.models.user import Utilisateur

app = create_app()

with app.app_context():
    admin = Utilisateur.query.filter_by(username='admin').first()
    if admin:
        admin.set_password('1234')
        db.session.commit()
        print("Admin password updated to 1234.")
    else:
        print("Admin user not found.")
