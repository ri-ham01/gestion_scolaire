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
        # Find available suffix for student
        for i in range(1, 100):
            proposed = f'26mathA_{i}'
            if not Utilisateur.query.filter_by(username=proposed).first():
                student.username = proposed
                break
        student.password_hash = generate_password_hash('123')
        print(f"Updated student to {student.username}")

    print("Correcting teacher usernames and passwords...")
    # Find available suffixes for teachers
    def get_teacher_username():
        for i in range(1, 100):
            proposed = f'prof_math{i}'
            if not Utilisateur.query.filter_by(username=proposed).first():
                return proposed
        return None

    teacher1 = Utilisateur.query.filter_by(username='prof_analyse').first()
    if teacher1:
        teacher1.username = get_teacher_username()
        teacher1.password_hash = generate_password_hash('123')
        # commit to register the username
        db.session.commit()
        print(f"Updated teacher1 to {teacher1.username}")

    teacher2 = Utilisateur.query.filter_by(username='prof_algebre').first()
    if teacher2:
        teacher2.username = get_teacher_username()
        teacher2.password_hash = generate_password_hash('123')
        db.session.commit()
        print(f"Updated teacher2 to {teacher2.username}")

    teacher3 = Utilisateur.query.filter_by(username='prof_proba').first()
    if teacher3:
        teacher3.username = get_teacher_username()
        teacher3.password_hash = generate_password_hash('123')
        db.session.commit()
        print(f"Updated teacher3 to {teacher3.username}")

    print("SUCCESS: Usernames and passwords updated according to convention.")

except Exception as e:
    db.session.rollback()
    print(f"ERROR: {e}")
