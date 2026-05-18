# =============================================================
#  EduNova — blueprints/public/routes.py
#  Pages publiques : Home, EDT, Examens, Annonces, Cours public
#  Vérification QR relevé
# =============================================================
import os
from flask import (render_template, send_file, abort,
                   redirect, url_for, request, current_app, jsonify)
from app.blueprints.public import public_bp
from app.extensions import db
from app.models.academic import AnneeScolaire, Semestre, Specialite
from app.models.communication import Annonce
from app.models.planning import PdfEmploiTemps
from app.models.evaluation import ReleverNotes


@public_bp.route('/')
def index():
    annonces = (Annonce.query
                .filter_by(est_publie=True)
                .order_by(Annonce.est_epinglee.desc(), Annonce.date_publication.desc())
                .limit(3).all())
    return render_template('public/home.html', annonces=annonces)


# ── Emploi du temps ───────────────────────────────────────────
@public_bp.route('/emploi-du-temps')
def emploi_du_temps():
    specialites = Specialite.query.filter_by(est_active=True).order_by(Specialite.nom).all()
    semestre    = Semestre.query.filter_by(est_actif=True).first()
    return render_template('public/emploi_temps.html',
                           specialites=specialites, semestre=semestre)


@public_bp.route('/emploi-du-temps/telecharger/<int:spe_id>')
def telecharger_edt(spe_id):
    semestre = Semestre.query.filter_by(est_actif=True).first()
    if not semestre:
        abort(404)
    pdf_record = PdfEmploiTemps.query.filter_by(
        specialite_id=spe_id,
        semestre_id=semestre.id,
        type_pdf='hebdomadaire'
    ).first()
    if not pdf_record:
        abort(404)
    chemin = os.path.join(current_app.config['UPLOAD_FOLDER'],
                          *pdf_record.fichier_url.split('/')[1:])
    if not os.path.exists(chemin):
        abort(404)
    return send_file(chemin, as_attachment=True,
                     download_name=pdf_record.nom_fichier,
                     mimetype='application/pdf')


# ── Examens ───────────────────────────────────────────────────
@public_bp.route('/examens')
def examens():
    specialites = Specialite.query.filter_by(est_active=True).order_by(Specialite.nom).all()
    semestre    = Semestre.query.filter_by(est_actif=True).first()
    return render_template('public/examens.html',
                           specialites=specialites, semestre=semestre)


@public_bp.route('/examens/telecharger/<int:spe_id>')
def telecharger_examen(spe_id):
    semestre = Semestre.query.filter_by(est_actif=True).first()
    if not semestre:
        abort(404)
    pdf_record = PdfEmploiTemps.query.filter_by(
        specialite_id=spe_id,
        semestre_id=semestre.id,
        type_pdf='examens'
    ).first()
    if not pdf_record:
        abort(404)
    chemin = os.path.join(current_app.config['UPLOAD_FOLDER'],
                          *pdf_record.fichier_url.split('/')[1:])
    if not os.path.exists(chemin):
        abort(404)
    return send_file(chemin, as_attachment=True,
                     download_name=pdf_record.nom_fichier,
                     mimetype='application/pdf')


# ── Annonces ──────────────────────────────────────────────────
@public_bp.route('/annonces')
def annonces():
    page = request.args.get('page', 1, type=int)
    annonces_pag = (Annonce.query
                    .filter_by(est_publie=True)
                    .order_by(Annonce.est_epinglee.desc(),
                              Annonce.date_publication.desc())
                    .paginate(page=page, per_page=10, error_out=False))
    return render_template('public/annonces.html', annonces=annonces_pag)


# ── Cours public (sélection rôle) ────────────────────────────
@public_bp.route('/cours')
def cours_public():
    return render_template('public/cours_public.html')


# ── Vérification QR relevé ───────────────────────────────────
@public_bp.route('/verif-releve/<token>')
def verifier_releve(token):
    releve = ReleverNotes.query.filter_by(qr_code_token=token).first()
    if not releve:
        abort(404)
    chemin = os.path.join(current_app.config['UPLOAD_FOLDER'],
                          *releve.fichier_url.split('/')[1:])
    if not os.path.exists(chemin):
        abort(404)
    return send_file(chemin, as_attachment=True,
                     download_name=releve.nom_fichier or 'releve.pdf',
                     mimetype='application/pdf')


# ── Erreurs ───────────────────────────────────────────────────
@public_bp.app_errorhandler(403)
def forbidden(e):
    return render_template('public/error.html', code=403,
                           message='Accès refusé — vous n\'avez pas les droits nécessaires.'), 403


@public_bp.app_errorhandler(404)
def not_found(e):
    return render_template('public/error.html', code=404,
                           message='Page introuvable.'), 404


@public_bp.app_errorhandler(500)
def server_error(e):
    return render_template('public/error.html', code=500,
                           message='Erreur interne du serveur.'), 500
