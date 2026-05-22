import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models.user import Utilisateur
from app.models.program import AffectationEnseignement, Inscription
from app.models.academic import Section
from app.models.profiles import Professeur

app = create_app()

with app.app_context():
    print("--- Testing Student Login ---")
    stu = Utilisateur.query.filter_by(username='24infoA_1').first()
    if stu:
        print(f"Student found: {stu.username}, Active: {stu.est_actif}, Locked: {stu.is_locked}, Role: {stu.role}")
        print(f"Password Check for '123': {stu.check_password('123')}")
        # Reset password again just in case
        stu.set_password('123')
        db.session.commit()
        print(f"Password Check after forced reset: {stu.check_password('123')}")
    else:
        print("Student not found!")

    print("\n--- Linking Math Professor to Math Students ---")
    prof_user = Utilisateur.query.filter_by(username='prof_math1').first()
    if prof_user and prof_user.professeur:
        prof_id = prof_user.professeur.id
        from app.models.academic import Semestre, Section
        from app.models.program import Matiere
        
        section = Section.query.filter_by(code_section='A-MATH').first()
        if not section:
            section = Section.query.first()
            
        matiere = Matiere.query.first()
        semestre = Semestre.query.first()
        
        if section and matiere and semestre:
            aff = AffectationEnseignement.query.filter_by(professeur_id=prof_id, section_id=section.id).first()
            if not aff:
                aff = AffectationEnseignement(
                    professeur_id=prof_id,
                    matiere_id=matiere.id,
                    section_id=section.id,
                    semestre_id=semestre.id,
                    est_active=True
                )
                db.session.add(aff)
            
            # Assign students
            from datetime import datetime, timezone
            for uname in ['26mathA_10', '26mathA_1', '26mathA_2', '26mathA_3']:
                stu = Utilisateur.query.filter_by(username=uname).first()
                if stu:
                    insc = Inscription.query.filter_by(etudiant_id=stu.etudiant.id, section_id=section.id).first()
                    if not insc:
                        insc = Inscription(
                            etudiant_id=stu.etudiant.id,
                            section_id=section.id,
                            annee_scolaire_id=semestre.annee_scolaire_id,
                            statut='actif',
                            date_inscription=datetime.now(timezone.utc).date()
                        )
                        db.session.add(insc)
            db.session.commit()
            print("Math professor and students successfully linked!")
        else:
            print("Missing base data for Math.")
