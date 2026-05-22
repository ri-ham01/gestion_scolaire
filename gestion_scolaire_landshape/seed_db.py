import sys
import os

# Assuming running from e:\gestion scolaire\gestion_scolaire_landshape
sys.path.append(os.getcwd())

from app import create_app
from app.extensions import db
from app.models import Utilisateur
from app.models.profiles import Etudiant, Professeur
from app.models.academic import Specialite, Niveau, Section, AnneeScolaire, Semestre
from app.models.program import Programme, AffectationEnseignement, Inscription, Matiere
from werkzeug.security import generate_password_hash
from datetime import date

app = create_app()

with app.app_context():
    # Helper to generate passwords
    def create_user(username, role, password="password123"):
        user = Utilisateur.query.filter_by(username=username).first()
        if not user:
            user = Utilisateur(username=username, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
        return user

    annee_courante = AnneeScolaire.query.filter_by(est_active=True).first()
    sem1 = Semestre.query.filter_by(annee_scolaire_id=annee_courante.id, numero=1).first()
    sem2 = Semestre.query.filter_by(annee_scolaire_id=annee_courante.id, numero=2).first()

    # 1. Create Specialties & Levels
    spec_math = Specialite.query.filter_by(code='MATH').first()
    if not spec_math:
        spec_math = Specialite(code='MATH', nom='Mathématiques', description='Spécialité Mathématiques')
        db.session.add(spec_math)
    
    spec_info = Specialite.query.filter_by(code='INFO').first()
    if not spec_info:
        spec_info = Specialite(code='INFO', nom='Informatique', description='Spécialité Informatique')
        db.session.add(spec_info)
    
    db.session.flush()

    niv_1 = Niveau.query.filter_by(ordre=1).first()
    if not niv_1:
        niv_1 = Niveau(nom='Licence 1', ordre=1, description='Première année')
        db.session.add(niv_1)
    db.session.flush()

    # 2. Create Sections
    # Math sections
    sec_math_1 = Section.query.filter_by(code_section='MATH-L1-A').first()
    if not sec_math_1:
        sec_math_1 = Section(code_section='MATH-L1-A', niveau_id=niv_1.id, specialite_id=spec_math.id, annee_scolaire_id=annee_courante.id)
        db.session.add(sec_math_1)
    
    sec_math_2 = Section.query.filter_by(code_section='MATH-L1-B').first()
    if not sec_math_2:
        sec_math_2 = Section(code_section='MATH-L1-B', niveau_id=niv_1.id, specialite_id=spec_math.id, annee_scolaire_id=annee_courante.id)
        db.session.add(sec_math_2)

    # Info section
    sec_info_1 = Section.query.filter_by(code_section='INFO-L1-A').first()
    if not sec_info_1:
        sec_info_1 = Section(code_section='INFO-L1-A', niveau_id=niv_1.id, specialite_id=spec_info.id, annee_scolaire_id=annee_courante.id)
        db.session.add(sec_info_1)

    db.session.flush()

    # 3. Create Students
    # 10 students for MATH-L1-A
    for i in range(1, 11):
        username = f"mathA_{i}"
        user = create_user(username, 'etudiant')
        etu = Etudiant.query.filter_by(utilisateur_id=user.id).first()
        if not etu:
            etu = Etudiant(
                utilisateur_id=user.id, nom=f"NomA{i}", prenom=f"Prenom{i}",
                date_naissance=date(2005, 1, 1), lieu_naissance="Alger",
                adresse="Alger", telephone=f"05500000{i:02d}", matricule=f"MAT-A-{i:03d}"
            )
            db.session.add(etu)
            db.session.flush()
            # Inscription
            insc = Inscription(etudiant_id=etu.id, section_id=sec_math_1.id, annee_scolaire_id=annee_courante.id, semestre_courant=1, statut='actif', date_inscription=date.today())
            db.session.add(insc)

    # 10 students for MATH-L1-B
    for i in range(1, 11):
        username = f"mathB_{i}"
        user = create_user(username, 'etudiant')
        etu = Etudiant.query.filter_by(utilisateur_id=user.id).first()
        if not etu:
            etu = Etudiant(
                utilisateur_id=user.id, nom=f"NomB{i}", prenom=f"Prenom{i}",
                date_naissance=date(2005, 1, 1), lieu_naissance="Alger",
                adresse="Alger", telephone=f"05510000{i:02d}", matricule=f"MAT-B-{i:03d}"
            )
            db.session.add(etu)
            db.session.flush()
            # Inscription
            insc = Inscription(etudiant_id=etu.id, section_id=sec_math_2.id, annee_scolaire_id=annee_courante.id, semestre_courant=1, statut='actif', date_inscription=date.today())
            db.session.add(insc)

    # Info students (let's add 5 just to have some)
    for i in range(1, 6):
        username = f"infoA_{i}"
        user = create_user(username, 'etudiant')
        etu = Etudiant.query.filter_by(utilisateur_id=user.id).first()
        if not etu:
            etu = Etudiant(
                utilisateur_id=user.id, nom=f"NomI{i}", prenom=f"Prenom{i}",
                date_naissance=date(2005, 1, 1), lieu_naissance="Oran",
                adresse="Oran", telephone=f"05520000{i:02d}", matricule=f"INF-A-{i:03d}"
            )
            db.session.add(etu)
            db.session.flush()
            # Inscription
            insc = Inscription(etudiant_id=etu.id, section_id=sec_info_1.id, annee_scolaire_id=annee_courante.id, semestre_courant=1, statut='actif', date_inscription=date.today())
            db.session.add(insc)

    # 4. Create Subjects
    mat_logique = Matiere.query.filter_by(code='LOG101').first()
    if not mat_logique:
        mat_logique = Matiere(code='LOG101', nom='Logique', description='Logique Mathématique')
        db.session.add(mat_logique)

    mat_analyse = Matiere.query.filter_by(code='ANA101').first()
    if not mat_analyse:
        mat_analyse = Matiere(code='ANA101', nom='Analyse', description='Analyse Mathématique')
        db.session.add(mat_analyse)

    mat_geo = Matiere.query.filter_by(code='GEO101').first()
    if not mat_geo:
        mat_geo = Matiere(code='GEO101', nom='Géométrie', description='Géométrie Analytique')
        db.session.add(mat_geo)

    mat_algo = Matiere.query.filter_by(code='ALG101').first()
    if not mat_algo:
        mat_algo = Matiere(code='ALG101', nom='Algorithmique', description='Algorithmique de base')
        db.session.add(mat_algo)
        
    db.session.flush()

    # Create Programmes (S1 only for simplicity, or S1 and S2)
    # Math: Logique (main, 3), Analyse (main, 4), Geo (secondary, 2)
    def add_programme(mat_id, spec_id, niv_id, sem_num, coeff, type_mat):
        prog = Programme.query.filter_by(matiere_id=mat_id, specialite_id=spec_id, niveau_id=niv_id, semestre_numero=sem_num).first()
        if not prog:
            prog = Programme(matiere_id=mat_id, specialite_id=spec_id, niveau_id=niv_id, semestre_numero=sem_num, coefficient=coeff, type_matiere=type_mat)
            db.session.add(prog)

    add_programme(mat_logique.id, spec_math.id, niv_1.id, 1, 3, 'principale')
    add_programme(mat_analyse.id, spec_math.id, niv_1.id, 1, 4, 'principale')
    add_programme(mat_geo.id, spec_math.id, niv_1.id, 1, 2, 'secondaire')
    
    # Info: Logique (main, 3), Algo (secondary, 2)
    add_programme(mat_logique.id, spec_info.id, niv_1.id, 1, 3, 'principale')
    add_programme(mat_algo.id, spec_info.id, niv_1.id, 1, 2, 'secondaire')

    # 5. Create Professors
    # Prof Logique
    u_plog = create_user("prof_logique", "professeur")
    p_log = Professeur.query.filter_by(utilisateur_id=u_plog.id).first()
    if not p_log:
        p_log = Professeur(utilisateur_id=u_plog.id, matricule="P-LOG-01", nom="Prof", prenom="Logique", email_professionnel="prof_logique@edu.dz")
        db.session.add(p_log)
    
    # Prof Analyse 1
    u_pana1 = create_user("prof_analyse1", "professeur")
    p_ana1 = Professeur.query.filter_by(utilisateur_id=u_pana1.id).first()
    if not p_ana1:
        p_ana1 = Professeur(utilisateur_id=u_pana1.id, matricule="P-ANA-01", nom="Prof", prenom="Analyse1", email_professionnel="prof_analyse1@edu.dz")
        db.session.add(p_ana1)

    # Prof Analyse 2
    u_pana2 = create_user("prof_analyse2", "professeur")
    p_ana2 = Professeur.query.filter_by(utilisateur_id=u_pana2.id).first()
    if not p_ana2:
        p_ana2 = Professeur(utilisateur_id=u_pana2.id, matricule="P-ANA-02", nom="Prof", prenom="Analyse2", email_professionnel="prof_analyse2@edu.dz")
        db.session.add(p_ana2)

    # Prof Geo
    u_pgeo = create_user("prof_geo", "professeur")
    p_geo = Professeur.query.filter_by(utilisateur_id=u_pgeo.id).first()
    if not p_geo:
        p_geo = Professeur(utilisateur_id=u_pgeo.id, matricule="P-GEO-01", nom="Prof", prenom="Geo", email_professionnel="prof_geo@edu.dz")
        db.session.add(p_geo)

    # Prof Algo
    u_palgo = create_user("prof_algo", "professeur")
    p_algo = Professeur.query.filter_by(utilisateur_id=u_palgo.id).first()
    if not p_algo:
        p_algo = Professeur(utilisateur_id=u_palgo.id, matricule="P-ALG-01", nom="Prof", prenom="Algo", email_professionnel="prof_algo@edu.dz")
        db.session.add(p_algo)

    db.session.flush()

    # 6. Affectations (Assign Profs to sections/subjects)
    def add_affectation(prof_id, mat_id, sec_id, sem_id):
        aff = AffectationEnseignement.query.filter_by(professeur_id=prof_id, matiere_id=mat_id, section_id=sec_id, semestre_id=sem_id).first()
        if not aff:
            aff = AffectationEnseignement(professeur_id=prof_id, matiere_id=mat_id, section_id=sec_id, semestre_id=sem_id, est_active=True)
            db.session.add(aff)
    
    # Prof Logique teaches Math Section A & B AND Info Section A
    add_affectation(p_log.id, mat_logique.id, sec_math_1.id, sem1.id)
    add_affectation(p_log.id, mat_logique.id, sec_math_2.id, sem1.id)
    add_affectation(p_log.id, mat_logique.id, sec_info_1.id, sem1.id)

    # Prof Analyse 1 teaches Math Section A
    add_affectation(p_ana1.id, mat_analyse.id, sec_math_1.id, sem1.id)

    # Prof Analyse 2 teaches Math Section B
    add_affectation(p_ana2.id, mat_analyse.id, sec_math_2.id, sem1.id)

    # Prof Geo teaches Math Section A & B
    add_affectation(p_geo.id, mat_geo.id, sec_math_1.id, sem1.id)
    add_affectation(p_geo.id, mat_geo.id, sec_math_2.id, sem1.id)

    # Prof Algo teaches Info Section A
    add_affectation(p_algo.id, mat_algo.id, sec_info_1.id, sem1.id)

    db.session.commit()
    print("Database seeded successfully with the required students, subjects, and professors.")
