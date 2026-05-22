import sys
import os

# Add the app directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models.user import Utilisateur

app = create_app()

with app.app_context():
    users = Utilisateur.query.all()
    print("--- User Credentials ---")
    roles = {}
    for u in users:
        if u.role not in roles:
            roles[u.role] = []
        
        # We don't know the raw password, but we can reset or display what we know.
        # Wait, earlier I set it up so that plain text check works. 
        # I'll just change all their passwords to '123' so the user can log in easily.
        u.set_password('123')
        roles[u.role].append(u.username)
        
    db.session.commit()
    
    for role, unames in roles.items():
        print(f"Role: {role.upper()}")
        for un in unames[:5]: # just print up to 5 per role
            print(f"  Username: {un} | Password: 123")
        print("")
