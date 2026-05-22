import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models.user import Utilisateur

app = create_app()

with app.app_context():
    users = Utilisateur.query.all()
    with open("user_report.md", "w", encoding="utf-8") as f:
        f.write("# Rapport des Utilisateurs\n\n")
        
        # Etudiants
        f.write("## Étudiants\n")
        f.write("| ID | Username | Nom Complet | Actif | Lock |\n")
        f.write("|---|---|---|---|---|\n")
        for u in users:
            if u.role == 'etudiant':
                name = f"{u.etudiant.prenom} {u.etudiant.nom}" if u.etudiant else "N/A"
                f.write(f"| {u.id} | `{u.username}` | {name} | {u.est_actif} | {u.is_locked} |\n")
                
        # Professeurs
        f.write("\n## Professeurs\n")
        f.write("| ID | Username | Nom Complet | Actif | Lock |\n")
        f.write("|---|---|---|---|---|\n")
        for u in users:
            if u.role == 'professeur':
                name = f"{u.professeur.prenom} {u.professeur.nom}" if u.professeur else "N/A"
                f.write(f"| {u.id} | `{u.username}` | {name} | {u.est_actif} | {u.is_locked} |\n")

        # Admin
        f.write("\n## Admins\n")
        for u in users:
            if u.role == 'admin':
                f.write(f"- `{u.username}`\n")
                
    print("Report generated successfully.")
