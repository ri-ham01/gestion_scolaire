import datetime
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models.academic import AnneeScolaire, Semestre, Specialite, Niveau, Section
from app.models.program import Matiere, AffectationEnseignement, Inscription
from app.models.user import Utilisateur
from app.models.profiles import Professeur, Etudiant, Parent
from app.services.auth_service import creer_compte_etudiant, creer_compte_professeur, creer_compte_parent

app = create_app()

with app.app_context():
    # 1. Annee Scolaire
    annee = AnneeScolaire.query.filter_by(annee_debut=2026).first()
    if not annee:
        print("Année 2026 non trouvée. Veuillez relancer seed_math.py d'abord.")
        exit(1)

    s1 = Semestre.query.filter_by(annee_scolaire_id=annee.id, numero=1).first()
    niveau = Niveau.query.filter_by(ordre=1).first()

    # 2. Specialite Informatique
    spe = Specialite.query.filter_by(code='INFO').first()
    if not spe:
        spe = Specialite(code='INFO', nom='Informatique', est_active=True)
        db.session.add(spe)
        db.session.flush()

    # 3. Matieres ALGO et PHP
    mat_algo = Matiere.query.filter_by(code='ALGO101').first()
    if not mat_algo:
        mat_algo = Matiere(code='ALGO101', nom='Algorithmique et Structures de Données')
        db.session.add(mat_algo)
        
    mat_php = Matiere.query.filter_by(code='PHP101').first()
    if not mat_php:
        mat_php = Matiere(code='PHP101', nom='Développement Web PHP')
        db.session.add(mat_php)
        
    db.session.flush()

    # 4. Section INFO-G1
    sec1 = Section.query.filter_by(code_section='INFO-G1', specialite_id=spe.id, niveau_id=niveau.id, annee_scolaire_id=annee.id).first()
    if not sec1:
        sec1 = Section(code_section='INFO-G1', specialite_id=spe.id, niveau_id=niveau.id, annee_scolaire_id=annee.id)
        db.session.add(sec1)
        db.session.flush()

    # 5. Professeurs
    user_algo = Utilisateur.query.filter_by(username='prof_algo01').first()
    if not user_algo:
        user_algo, pwd = creer_compte_professeur(nom="Prof", prenom="Algorithme", specialite_code="INFO")
        user_algo.username = 'prof_algo01'
        user_algo.password_hash = generate_password_hash('123')
        db.session.flush()
    prof_algo = Professeur.query.filter_by(utilisateur_id=user_algo.id).first()

    user_php = Utilisateur.query.filter_by(username='prof_php01').first()
    if not user_php:
        user_php, pwd = creer_compte_professeur(nom="Prof", prenom="PHP", specialite_code="INFO")
        user_php.username = 'prof_php01'
        user_php.password_hash = generate_password_hash('123')
        db.session.flush()
    prof_php = Professeur.query.filter_by(utilisateur_id=user_php.id).first()

    # Affectations
    aff1 = AffectationEnseignement.query.filter_by(professeur_id=prof_algo.id, section_id=sec1.id, matiere_id=mat_algo.id, semestre_id=s1.id).first()
    if not aff1:
        db.session.add(AffectationEnseignement(professeur_id=prof_algo.id, section_id=sec1.id, matiere_id=mat_algo.id, semestre_id=s1.id))
    
    aff2 = AffectationEnseignement.query.filter_by(professeur_id=prof_php.id, section_id=sec1.id, matiere_id=mat_php.id, semestre_id=s1.id).first()
    if not aff2:
        db.session.add(AffectationEnseignement(professeur_id=prof_php.id, section_id=sec1.id, matiere_id=mat_php.id, semestre_id=s1.id))
        
    db.session.flush()

    # 6. Etudiants (12)
    noms_prenoms = [
        ("Amira", "Saidi"), ("Nassim", "Bouzid"), ("Sarah", "Khelifi"), ("Mehdi", "Meziane"), ("Rania", "Zidani"),
        ("Yanis", "Belaid"), ("Nour", "Abbas"), ("Adil", "Djabali"), ("Lina", "Chergui"), ("Samy", "Kacimi"),
        ("Chaima", "Othmani"), ("Zaki", "Bennacer")
    ]
    
    for i, (prenom, nom) in enumerate(noms_prenoms):
        existing_etu = Etudiant.query.filter_by(nom=nom, prenom=prenom).first()
        if existing_etu:
            continue
            
        try:
            # Create Etudiant
            user_etu, pwd = creer_compte_etudiant(
                nom=nom, prenom=prenom, specialite_code="INFO", niveau_ordre=1, annee_debut=2026
            )
            db.session.flush()
            
            # Inscription
            insc = Inscription(etudiant_id=user_etu.etudiant.id, section_id=sec1.id, annee_scolaire_id=annee.id, date_inscription=datetime.date.today())
            db.session.add(insc)
            
            # Create Parent
            parent_email = f"parent.{prenom.lower()}.{nom.lower()}@edu.nova.dz"
            parent_nom = nom
            parent_prenom = f"Parent de {prenom}"
            
            user_parent, parent_pwd = creer_compte_parent(
                nom=parent_nom, prenom=parent_prenom, email=parent_email, telephone="0000000000"
            )
            # Force parent password
            user_parent.password_hash = generate_password_hash('12345')
            db.session.flush()
            
            # Link Parent and Etudiant
            from app.models.profiles import ParentEtudiant
            lien = ParentEtudiant(parent_id=user_parent.parent.id, etudiant_id=user_etu.etudiant.id, relation="Père")
            db.session.add(lien)
            
        except Exception as e:
            print(f"Skipping {prenom} {nom} due to error: {str(e)}")
            
    db.session.commit()
    print("Seed Informatique completed successfully.")
