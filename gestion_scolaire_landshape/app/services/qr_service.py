# =============================================================
#  EduNova — services/qr_service.py
#  Génération QR codes pour relevés de notes
# =============================================================
import os
import qrcode
from qrcode.image.pil import PilImage
from flask import current_app, url_for


def generer_qr_releve(token: str) -> str:
    """
    Génère un QR code PNG qui pointe vers /verif-releve/<token>.
    Retourne le chemin absolu de l'image générée.
    """
    try:
        url = url_for('public.verifier_releve', token=token, _external=True)
    except RuntimeError:
        url = f'http://localhost:5000/verif-releve/{token}'

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color='#4F46E5', back_color='white')

    dossier = os.path.join(current_app.config['UPLOAD_FOLDER'], 'releves', 'qr')
    os.makedirs(dossier, exist_ok=True)
    chemin  = os.path.join(dossier, f'qr_{token}.png')
    img.save(chemin)
    return chemin


def chemin_qr_relatif(token: str) -> str:
    return f'uploads/releves/qr/qr_{token}.png'


# =============================================================
#  EduNova — services/presence_service.py
#  Enregistrement présence et compteurs
# =============================================================

def enregistrer_presences(affectation_id: int, professeur_id: int,
                           date_seance, heure_debut, heure_fin,
                           type_seance: str,
                           presences_data: list[dict]) -> bool:
    """
    Crée une Seance puis enregistre les présences de chaque étudiant.
    presences_data = [{'etudiant_id': X, 'statut': 'present'|'absent'}, ...]
    Déclenche les notifications pour les absences.
    """
    from app.extensions import db
    from app.models.presence  import Seance, Presence, CompteurAbsences
    from app.models.program   import Inscription, AffectationEnseignement
    from app.models.academic  import Semestre
    from app.services.notif_service import notifier_absence

    try:
        # Créer la séance
        seance = Seance(
            affectation_id=affectation_id,
            date_seance=date_seance,
            heure_debut=heure_debut,
            heure_fin=heure_fin,
            type_seance=type_seance,
        )
        db.session.add(seance)
        db.session.flush()

        aff = db.session.get(AffectationEnseignement, affectation_id)

        for item in presences_data:
            etu_id = item['etudiant_id']
            statut = item.get('statut', 'present')

            pres = Presence(
                seance_id      = seance.id,
                etudiant_id    = etu_id,
                statut         = statut,
                enregistre_par = professeur_id,
            )
            db.session.add(pres)

            # Mettre à jour le compteur
            insc = Inscription.query.filter_by(
                etudiant_id=etu_id, statut='actif'
            ).first()
            if insc:
                compteur = CompteurAbsences.query.filter_by(
                    etudiant_id=etu_id,
                    inscription_id=insc.id,
                    semestre_id=aff.semestre_id
                ).first()
                if not compteur:
                    compteur = CompteurAbsences(
                        etudiant_id=etu_id,
                        inscription_id=insc.id,
                        semestre_id=aff.semestre_id,
                    )
                    db.session.add(compteur)
                    db.session.flush()

                compteur.total_seances += 1
                if statut == 'absent':
                    compteur.incrementer_absence(justifiee=False)

            # Notification absence
            if statut == 'absent':
                db.session.flush()
                notifier_absence(etu_id, seance.id)

        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Erreur enregistrement présences: {e}')
        return False


# Make importable from services package
def generer_qr_et_url(token: str):
    chemin = generer_qr_releve(token)
    return chemin, chemin_qr_relatif(token)
