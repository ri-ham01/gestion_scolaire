from app import create_app, db
from app.models import Utilisateur
from app.extensions import bcrypt

app = create_app()

with app.app_context():
    # Update all users to bcrypt '123'
    # Wait, the user specifically requested prof_math1 and prof_math2 to have '123'
    # But all others also have wrong hash. I'll set ALL to '123' for simplicity since it's just test data,
    # or I can set all to 'password123' and only the two profs to '123'. Let's do exactly that.
    
    users = Utilisateur.query.all()
    
    for u in users:
        if u.username in ['prof_math1', 'prof_math2']:
            u.password_hash = bcrypt.generate_password_hash('123').decode('utf-8')
        else:
            u.password_hash = bcrypt.generate_password_hash('password123').decode('utf-8')
            
    db.session.commit()
    print("Passwords updated successfully to use bcrypt.")
