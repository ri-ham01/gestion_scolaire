import sys
sys.path.append('.')

from app import create_app
from app.extensions import db
from app.models.user import Utilisateur
from app.models.profiles import Professeur, Etudiant
from app.models.academic import Specialite, Niveau, AnneeScolaire, Semestre, Section
from app.models.program import Matiere, Programme, AffectationEnseignement, Inscription
from app.models.evaluation import Note
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone

app = create_app()
app.app_context().push()

try:
    print("Fetching active school year and semester...")
    annee = AnneeScolaire.query.filter_by(est_active=True).first()
    if not annee:
        annee = AnneeScolaire.query.first()
    
    semestre = Semestre.query.filter_by(annee_scolaire_id=annee.id, numero=1).first()
    if not semestre:
        semestre = Semestre.query.filter_by(annee_scolaire_id=annee.id).first()

    print("Fetching Mathematics Specialite...")
    math_spe = Specialite.query.filter(Specialite.nom.ilike('%math%')).first()
    if not math_spe:
        math_spe = Specialite(code='MATH', nom='Mathématiques', description='Filière de Mathématiques')
        db.session.add(math_spe)
        db.session.flush()

    niveau = Niveau.query.first()
    
    print("Finding or creating Mathematics Section A...")
    section = Section.query.filter_by(specialite_id=math_spe.id, code_section='A', annee_scolaire_id=annee.id).first()
    if not section:
        section = Section(code_section='A', specialite_id=math_spe.id, niveau_id=niveau.id, annee_scolaire_id=annee.id, capacite_max=35)
        db.session.add(section)
        db.session.flush()

    print("Checking for a student in this section...")
    inscription = Inscription.query.filter_by(section_id=section.id, statut='actif').first()
    etudiant = None
    if not inscription:
        # Need to create a dummy student
        user_e = Utilisateur(username='etudiant_math', password_hash=generate_password_hash('password123'), role='etudiant')
        db.session.add(user_e)
        db.session.flush()
        
        etudiant = Etudiant(utilisateur_id=user_e.id, matricule='MAT001', nom='Doe', prenom='John')
        db.session.add(etudiant)
        db.session.flush()
        
        inscription = Inscription(etudiant_id=etudiant.id, section_id=section.id, annee_scolaire_id=annee.id, date_inscription=datetime.now(timezone.utc).date())
        db.session.add(inscription)
        db.session.flush()
    else:
        etudiant = inscription.etudiant

    # Create 3 subjects
    subjects_data = [
        {'code': 'ANA1', 'nom': 'Analyse Mathématique 1'},
        {'code': 'ALG1', 'nom': 'Algèbre Linéaire 1'},
        {'code': 'PROBA', 'nom': 'Probabilités et Statistiques'}
    ]
    
    teachers_data = [
        {'username': 'prof_analyse', 'nom': 'Smith', 'prenom': 'Alice', 'matricule': 'PROF001'},
        {'username': 'prof_algebre', 'nom': 'Johnson', 'prenom': 'Bob', 'matricule': 'PROF002'},
        {'username': 'prof_proba', 'nom': 'Williams', 'prenom': 'Charlie', 'matricule': 'PROF003'}
    ]
    
    for i in range(3):
        # Matiere
        mat = Matiere.query.filter_by(code=subjects_data[i]['code']).first()
        if not mat:
            mat = Matiere(code=subjects_data[i]['code'], nom=subjects_data[i]['nom'])
            db.session.add(mat)
            db.session.flush()
            
            prog = Programme(matiere_id=mat.id, specialite_id=math_spe.id, niveau_id=niveau.id, semestre_numero=semestre.numero, coefficient=3)
            db.session.add(prog)
            db.session.flush()

        # Professeur
        user_p = Utilisateur.query.filter_by(username=teachers_data[i]['username']).first()
        if not user_p:
            user_p = Utilisateur(username=teachers_data[i]['username'], password_hash=generate_password_hash('password123'), role='professeur')
            db.session.add(user_p)
            db.session.flush()
            
            prof = Professeur(utilisateur_id=user_p.id, matricule=teachers_data[i]['matricule'], nom=teachers_data[i]['nom'], prenom=teachers_data[i]['prenom'])
            db.session.add(prof)
            db.session.flush()
        else:
            prof = user_p.professeur

        # AffectationEnseignement
        aff = AffectationEnseignement.query.filter_by(professeur_id=prof.id, matiere_id=mat.id, section_id=section.id, semestre_id=semestre.id).first()
        if not aff:
            aff = AffectationEnseignement(professeur_id=prof.id, matiere_id=mat.id, section_id=section.id, semestre_id=semestre.id, date_affectation=datetime.now(timezone.utc).date())
            db.session.add(aff)
            db.session.flush()

        # Initialize empty Note for the student so it appears in the gradebook
        note = Note.query.filter_by(etudiant_id=etudiant.id, affectation_id=aff.id).first()
        if not note:
            # We don't add grades so the teacher can do it! Or we could add 0 to make it appear, but it's optional.
            # Let's just create a blank Note record
            pass

    db.session.commit()
    print("SUCCESS: 3 teachers and 3 subjects added and assigned to Math Section A.")
    print(f"Student Username: {etudiant.utilisateur.username} / Password: password123")
    print("Teachers:")
    for t in teachers_data:
        print(f"  Username: {t['username']} / Password: password123")

except Exception as e:
    db.session.rollback()
    print(f"ERROR: {e}")
