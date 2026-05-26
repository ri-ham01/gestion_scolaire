import sys
sys.path.append('.')

from app import create_app
from app.extensions import db
from app.models.user import Utilisateur
from werkzeug.security import generate_password_hash

app = create_app()
app.app_context().push()

try:
    print("Correcting student username and password...")
    student = Utilisateur.query.filter_by(username='etudiant_math').first()
    if student:
        # Check if 26mathA_1 is taken
        if Utilisateur.query.filter_by(username='26mathA_1').first():
            student.username = '26mathA_2'
        else:
            student.username = '26mathA_1'
        student.password_hash = generate_password_hash('123')
        print(f"Updated student to {student.username}")

    print("Correcting teacher usernames and passwords...")
    teacher1 = Utilisateur.query.filter_by(username='prof_analyse').first()
    if teacher1:
        teacher1.username = 'prof_math1'
        teacher1.password_hash = generate_password_hash('123')
        print(f"Updated teacher1 to {teacher1.username}")

    teacher2 = Utilisateur.query.filter_by(username='prof_algebre').first()
    if teacher2:
        teacher2.username = 'prof_math2'
        teacher2.password_hash = generate_password_hash('123')
        print(f"Updated teacher2 to {teacher2.username}")

    teacher3 = Utilisateur.query.filter_by(username='prof_proba').first()
    if teacher3:
        teacher3.username = 'prof_math3'
        teacher3.password_hash = generate_password_hash('123')
        print(f"Updated teacher3 to {teacher3.username}")

    db.session.commit()
    print("SUCCESS: Usernames and passwords updated according to convention.")

except Exception as e:
    db.session.rollback()
    print(f"ERROR: {e}")
