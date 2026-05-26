import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Ajouter le répertoire courant au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    print("1. Création des tables de la base de données...")
    db.create_all()
    print("Tables créées avec succès !")

print("\n2. Création de l'administration...")
import ensure_admin

print("\n3. Création du département Mathématiques (étudiants, professeurs, sections)...")
import seed_math

print("\n4. Création du département Informatique (étudiants, parents, professeurs)...")
import seed_info

print("\n=======================================================")
print("Initialisation de la base de données locale terminée avec succès !")
print("Vous pouvez maintenant lancer le site avec : python run.py")
print("=======================================================")
