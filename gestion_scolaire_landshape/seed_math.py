import datetime
from app import create_app, db
from app.models.academic import AnneeScolaire, Semestre, Specialite, Niveau, Section
from app.models.program import Matiere, AffectationEnseignement, Inscription
from app.models.user import Utilisateur
from app.models.profiles import Professeur, Etudiant
from app.services.auth_service import creer_compte_etudiant, creer_compte_professeur

app = create_app()

with app.app_context():
    # 1. Annee Scolaire 2026-2027
    annee = AnneeScolaire.query.filter_by(annee_debut=2026).first()
    if not annee:
        annee = AnneeScolaire(label="2026-2027", annee_debut=2026, annee_fin=2027, est_active=True)
        db.session.add(annee)
        db.session.flush()
        
        # 2 semestres de 6 mois
        d1_start = datetime.date(2026, 9, 1)
        d1_end   = datetime.date(2027, 2, 28)
        d2_start = datetime.date(2027, 3, 1)
        d2_end   = datetime.date(2027, 8, 31)
        
        s1 = Semestre(annee_scolaire_id=annee.id, numero=1, date_debut=d1_start, date_fin=d1_end, est_actif=True)
        s2 = Semestre(annee_scolaire_id=annee.id, numero=2, date_debut=d2_start, date_fin=d2_end, est_actif=False)
        db.session.add(s1)
        db.session.add(s2)
        db.session.flush()
    else:
        # Assure that annee is active
        AnneeScolaire.query.update({'est_active': False})
        annee.est_active = True
        db.session.commit()

    s1 = Semestre.query.filter_by(annee_scolaire_id=annee.id, numero=1).first()

    # 2. Niveau
    niveau = Niveau.query.filter_by(ordre=1).first()
    if not niveau:
        niveau = Niveau(nom="Première Année", ordre=1, est_actif=True)
        db.session.add(niveau)
        db.session.flush()

    # 3. Specialite Math
    spe = Specialite.query.filter_by(code='MATH').first()
    if not spe:
        spe = Specialite(code='MATH', nom='Mathématiques', est_active=True)
        db.session.add(spe)
        db.session.flush()

    # 4. Matiere
    mat = Matiere.query.filter_by(code='MATH101').first()
    if not mat:
        mat = Matiere(code='MATH101', nom='Analyse Mathématique 1')
        db.session.add(mat)
        db.session.flush()

    # 5. Sections (2 groupes)
    sec1 = Section.query.filter_by(code_section='G1', specialite_id=spe.id, niveau_id=niveau.id, annee_scolaire_id=annee.id).first()
    if not sec1:
        sec1 = Section(code_section='G1', specialite_id=spe.id, niveau_id=niveau.id, annee_scolaire_id=annee.id)
        db.session.add(sec1)
        
    sec2 = Section.query.filter_by(code_section='G2', specialite_id=spe.id, niveau_id=niveau.id, annee_scolaire_id=annee.id).first()
    if not sec2:
        sec2 = Section(code_section='G2', specialite_id=spe.id, niveau_id=niveau.id, annee_scolaire_id=annee.id)
        db.session.add(sec2)
        
    db.session.flush()

    # 6. Professeur de math
    user_prof = Utilisateur.query.filter_by(username='prof_math1').first()
    if not user_prof:
        user_prof, pwd = creer_compte_professeur(nom="Al Khwarizmi", prenom="Prof", specialite_code="MATH")
        db.session.flush()
    prof = Professeur.query.filter_by(utilisateur_id=user_prof.id).first()

    # Affecter le prof aux 2 sections
    aff1 = AffectationEnseignement.query.filter_by(professeur_id=prof.id, section_id=sec1.id, matiere_id=mat.id, semestre_id=s1.id).first()
    if not aff1:
        db.session.add(AffectationEnseignement(professeur_id=prof.id, section_id=sec1.id, matiere_id=mat.id, semestre_id=s1.id))
    
    aff2 = AffectationEnseignement.query.filter_by(professeur_id=prof.id, section_id=sec2.id, matiere_id=mat.id, semestre_id=s1.id).first()
    if not aff2:
        db.session.add(AffectationEnseignement(professeur_id=prof.id, section_id=sec2.id, matiere_id=mat.id, semestre_id=s1.id))
        
    db.session.flush()

    # 7. Etudiants (10 par section)
    etudiants_count = Inscription.query.filter(Inscription.section_id.in_([sec1.id, sec2.id])).count()
    credentials = []
    
    if etudiants_count < 20:
        noms_prenoms = [
            ("Ahmed", "Benali"), ("Karim", "Ziani"), ("Samira", "Kaddour"), ("Lina", "Brahimi"), ("Amine", "Toumi"),
            ("Sara", "Mansouri"), ("Yacine", "Boudiaf"), ("Nour", "Haddad"), ("Rami", "Saidi"), ("Ines", "Ammar"),
            ("Aymen", "Belkacem"), ("Sonia", "Djabou"), ("Omar", "Cherif"), ("Meriem", "Derradji"), ("Tarek", "Fares"),
            ("Leila", "Mebarek"), ("Walid", "Ghezzal"), ("Manal", "Bouziane"), ("Ilyes", "Yahiaoui"), ("Fatma", "Zouaghi")
        ]
        
        for i, (prenom, nom) in enumerate(noms_prenoms):
            section = sec1 if i < 10 else sec2
            # Check if user with same name already exists
            existing_etu = Etudiant.query.filter_by(nom=nom, prenom=prenom).first()
            if existing_etu:
                continue
                
            try:
                groupe_suffix = 'A' if section.code_section == 'G1' else 'B'
                user_etu, pwd = creer_compte_etudiant(
                    nom=nom, prenom=prenom, specialite_code="MATH", niveau_ordre=1, annee_debut=2026,
                    groupe_suffix=groupe_suffix
                )
                db.session.flush()
                # Inscription
                insc = Inscription(etudiant_id=user_etu.etudiant.id, section_id=section.id, annee_scolaire_id=annee.id, date_inscription=datetime.date.today())
                db.session.add(insc)
                credentials.append(f"{prenom} {nom} | Username: {user_etu.username} | Password: {pwd} | Section: {section.code_section}")
            except Exception as e:
                print(f"Skipping {prenom} {nom} due to error: {str(e)}")
                
    db.session.commit()
    print("Seed completed successfully.")
    for c in credentials:
        print(c)
