import random
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import Utilisateur, Etudiant, Professeur, Specialite, Section, Niveau, AnneeScolaire, Matiere, Programme

app = create_app()

def seed_database():
    with app.app_context():
        print("Début du peuplement de la base de données...")

        # 1. Vérifier ou créer l'année scolaire active
        annee = AnneeScolaire.query.filter_by(est_active=True).first()
        if not annee:
            annee = AnneeScolaire(
                label='2024-2025',
                annee_debut=2024,
                annee_fin=2025,
                est_active=True
            )
            db.session.add(annee)
            db.session.commit()
            print("Année scolaire 2024-2025 créée.")

        # 2. Créer les Niveaux s'ils n'existent pas
        niveau1 = Niveau.query.filter_by(ordre=1).first()
        if not niveau1:
            niveau1 = Niveau(nom='Première année', ordre=1)
            db.session.add(niveau1)
        niveau2 = Niveau.query.filter_by(ordre=2).first()
        if not niveau2:
            niveau2 = Niveau(nom='Deuxième année', ordre=2)
            db.session.add(niveau2)
        db.session.commit()

        # 3. Créer 2 Spécialités
        spe_info = Specialite.query.filter_by(code='INFO').first()
        if not spe_info:
            spe_info = Specialite(code='INFO', nom='Informatique', est_active=True)
            db.session.add(spe_info)
            
        spe_math = Specialite.query.filter_by(code='MATH').first()
        if not spe_math:
            spe_math = Specialite(code='MATH', nom='Mathématiques', est_active=True)
            db.session.add(spe_math)
        db.session.commit()

        # 4. Créer 2 Sections (1 pour chaque spécialité)
        sec_info = Section.query.filter_by(code_section='A-INFO').first()
        if not sec_info:
            sec_info = Section(code_section='A-INFO', specialite_id=spe_info.id, niveau_id=niveau1.id, annee_scolaire_id=annee.id)
            db.session.add(sec_info)

        sec_math = Section.query.filter_by(code_section='A-MATH').first()
        if not sec_math:
            sec_math = Section(code_section='A-MATH', specialite_id=spe_math.id, niveau_id=niveau1.id, annee_scolaire_id=annee.id)
            db.session.add(sec_math)
        db.session.commit()

        # 5. Créer 4 Professeurs (2 par section/spécialité)
        professeurs_data = [
            {'nom': 'Martin', 'prenom': 'Jean', 'username': 'prof_info1', 'spe': 'INFO'},
            {'nom': 'Dupont', 'prenom': 'Marie', 'username': 'prof_info2', 'spe': 'INFO'},
            {'nom': 'Bernard', 'prenom': 'Paul', 'username': 'prof_math1', 'spe': 'MATH'},
            {'nom': 'Thomas', 'prenom': 'Sophie', 'username': 'prof_math2', 'spe': 'MATH'},
        ]

        profs_crees = []
        for i, p_data in enumerate(professeurs_data, 1):
            user = Utilisateur.query.filter_by(username=p_data['username']).first()
            if not user:
                user = Utilisateur(
                    username=p_data['username'],
                    password_hash=generate_password_hash('password123'),
                    role='professeur',
                    email=f"{p_data['username']}@edunova.dz"
                )
                db.session.add(user)
                db.session.flush() # Pour avoir l'ID
                
                prof = Professeur(
                    utilisateur_id=user.id,
                    matricule=f'PROF{2024000+i}',
                    nom=p_data['nom'],
                    prenom=p_data['prenom'],
                    email_professionnel=f"{p_data['username']}@edunova.dz"
                )
                db.session.add(prof)
                profs_crees.append(prof)
        db.session.commit()

        # 6. Créer 10 Étudiants (5 par section)
        etudiants_data = [
            # Info
            {'nom': 'Lefebvre', 'prenom': 'Lucas', 'username': 'etu_info1'},
            {'nom': 'Moreau', 'prenom': 'Emma', 'username': 'etu_info2'},
            {'nom': 'Simon', 'prenom': 'Hugo', 'username': 'etu_info3'},
            {'nom': 'Laurent', 'prenom': 'Chloe', 'username': 'etu_info4'},
            {'nom': 'Michel', 'prenom': 'Leo', 'username': 'etu_info5'},
            # Math
            {'nom': 'Garcia', 'prenom': 'Camille', 'username': 'etu_math1'},
            {'nom': 'David', 'prenom': 'Louis', 'username': 'etu_math2'},
            {'nom': 'Richard', 'prenom': 'Alice', 'username': 'etu_math3'},
            {'nom': 'Roux', 'prenom': 'Arthur', 'username': 'etu_math4'},
            {'nom': 'Vincent', 'prenom': 'Juliette', 'username': 'etu_math5'},
        ]

        from app.models import Inscription
        
        for i, e_data in enumerate(etudiants_data, 1):
            user = Utilisateur.query.filter_by(username=e_data['username']).first()
            if not user:
                user = Utilisateur(
                    username=e_data['username'],
                    password_hash=generate_password_hash('password123'),
                    role='etudiant',
                    email=f"{e_data['username']}@student.edunova.dz"
                )
                db.session.add(user)
                db.session.flush()
                
                etu = Etudiant(
                    utilisateur_id=user.id,
                    matricule=f'ETU{2024000+i}',
                    nom=e_data['nom'],
                    prenom=e_data['prenom']
                )
                db.session.add(etu)
                db.session.flush()

                # Inscrire l'étudiant dans sa section (les 5 premiers en info, les 5 suivants en math)
                section_id = sec_info.id if i <= 5 else sec_math.id
                
                # Vérifier si l'inscription existe déjà
                ins = Inscription.query.filter_by(etudiant_id=etu.id, annee_scolaire_id=annee.id).first()
                if not ins:
                    from datetime import date
                    ins = Inscription(
                        etudiant_id=etu.id,
                        section_id=section_id,
                        annee_scolaire_id=annee.id,
                        date_inscription=date.today(),
                        statut='actif'
                    )
                    db.session.add(ins)
        
        db.session.commit()
        
        print("Base de données peuplée avec succès !")
        print("=======================================")
        print("Informations de connexion :")
        print("Mot de passe par défaut pour tous : password123")
        print("---------------------------------------")
        print("Professeurs INFO : prof_info1, prof_info2")
        print("Professeurs MATH : prof_math1, prof_math2")
        print("Étudiants INFO   : etu_info1 à etu_info5")
        print("Étudiants MATH   : etu_math1 à etu_math5")
        print("=======================================")

if __name__ == '__main__':
    seed_database()
