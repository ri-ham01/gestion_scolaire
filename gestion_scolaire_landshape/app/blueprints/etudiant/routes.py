# =============================================================
#  EduNova — blueprints/etudiant/routes.py
# =============================================================
import os
from datetime import datetime, timezone
from flask import (render_template, redirect, url_for, request,
                   flash, send_file, abort, jsonify, current_app)
from flask_login import login_required, current_user
from app.blueprints.etudiant import etudiant_bp
from app.extensions import db
from app.utils.decorators import etudiant_requis
from app.utils.helpers import chemin_absolu_upload
from app.models.profiles import Etudiant
from app.models.program import AffectationEnseignement, Inscription
from app.models.academic import AnneeScolaire, Semestre
from app.models.evaluation import Note, ResultatSemestre, ResultatAnnuel, ReleverNotes, CorrectionExamen
from app.models.pedagogy import Cours, Devoir, SoumissionDevoir, PostProfesseur
from app.models.communication import Conversation, Message, Notification
from app.services.notif_service import notifier_message


def get_etu() -> Etudiant:
    return current_user.etudiant


@etudiant_bp.route('/dashboard')
@login_required
@etudiant_requis
def dashboard():
    etu   = get_etu()
    insc  = etu.get_inscription_active()
    notifs_count = Notification.query.filter_by(
        destinataire_id=current_user.id, est_lu=False).count()
    
    annee_id = request.args.get('annee_id', type=int)
    sem_num  = request.args.get('sem', 1, type=int)
    if not annee_id and insc:
        annee_id = insc.annee_scolaire_id
        sem_num = insc.semestre_courant
        
    annees = AnneeScolaire.query.order_by(AnneeScolaire.annee_debut.desc()).all()
    affs = []
    
    if insc and annee_id:
        sem = Semestre.query.filter_by(
            annee_scolaire_id=annee_id, numero=sem_num).first()
        if sem:
            affs = AffectationEnseignement.query.filter_by(
                section_id=insc.section_id, semestre_id=sem.id).all()

    return render_template('etudiant/dashboard.html',
                           etu=etu, insc=insc, notifs_count=notifs_count, 
                           affs=affs, annees=annees, annee_id=annee_id, sem_num=sem_num)


# ── Notes & Bulletin ──────────────────────────────────────────
@etudiant_bp.route('/notes')
@login_required
@etudiant_requis
def notes():
    etu  = get_etu()
    insc = etu.get_inscription_active()
    if not insc:
        flash('Aucune inscription active trouvée.', 'warning')
        return redirect(url_for('etudiant.dashboard'))

    def get_notes_semestre(sem_num):
        sem = Semestre.query.filter_by(
            annee_scolaire_id=insc.annee_scolaire_id, numero=sem_num).first()
        if not sem:
            return [], None, None
        affs = AffectationEnseignement.query.filter_by(
            section_id=insc.section_id, semestre_id=sem.id, est_active=True).all()
        rows = []
        for aff in affs:
            note = Note.query.filter_by(
                etudiant_id=etu.id, affectation_id=aff.id).first()
            prog = next((p for p in aff.matiere.programmes
                         if p.specialite_id == insc.section.specialite_id
                         and p.niveau_id    == insc.section.niveau_id
                         and p.semestre_numero == sem_num), None)
            rows.append({'matiere': aff.matiere, 'note': note,
                         'coeff': prog.coefficient if prog else 1,
                         'type': prog.type_matiere if prog else 'principale'})
        rs = ResultatSemestre.query.filter_by(
            etudiant_id=etu.id, inscription_id=insc.id, semestre_id=sem.id).first()
        return rows, rs, sem

    rows_s1, rs1, sem1 = get_notes_semestre(1)
    rows_s2, rs2, sem2 = get_notes_semestre(2)
    ra = ResultatAnnuel.query.filter_by(
        etudiant_id=etu.id, annee_scolaire_id=insc.annee_scolaire_id).first()

    return render_template('etudiant/notes_bulletin.html',
                           etu=etu, insc=insc,
                           rows_s1=rows_s1, rs1=rs1, sem1=sem1,
                           rows_s2=rows_s2, rs2=rs2, sem2=sem2, ra=ra)


# ── Relevé de notes ───────────────────────────────────────────
@etudiant_bp.route('/releve')
@login_required
@etudiant_requis
def releve():
    etu   = get_etu()
    insc  = etu.get_inscription_active()
    
    def get_notes_semestre(sem_num):
        from app.models.academic import Semestre
        from app.models.program import AffectationEnseignement
        from app.models.evaluation import Note, ResultatSemestre
        if not insc:
            return [], None, None
        sem = Semestre.query.filter_by(
            annee_scolaire_id=insc.annee_scolaire_id, numero=sem_num).first()
        if not sem:
            return [], None, None
        affs = AffectationEnseignement.query.filter_by(
            section_id=insc.section_id, semestre_id=sem.id, est_active=True).all()
        rows = []
        for aff in affs:
            note = Note.query.filter_by(
                etudiant_id=etu.id, affectation_id=aff.id).first()
            prog = next((p for p in aff.matiere.programmes
                         if p.specialite_id == insc.section.specialite_id
                         and p.niveau_id    == insc.section.niveau_id
                         and p.semestre_numero == sem_num), None)
            rows.append({'matiere': aff.matiere, 'note': note,
                         'coeff': prog.coefficient if prog else 1,
                         'type': prog.type_matiere if prog else 'principale'})
        rs = ResultatSemestre.query.filter_by(
            etudiant_id=etu.id, inscription_id=insc.id, semestre_id=sem.id).first()
        return rows, rs, sem

    rows_s1, rs1, sem1 = get_notes_semestre(1)
    rows_s2, rs2, sem2 = get_notes_semestre(2)
    from app.models.evaluation import ResultatAnnuel
    ra = ResultatAnnuel.query.filter_by(
        etudiant_id=etu.id, annee_scolaire_id=insc.annee_scolaire_id if insc else 0).first()
        
    # Generate generic QR Code token
    token = f"stu_{etu.id}_{insc.id if insc else 0}"
    from app.services.qr_service import generer_qr_et_url
    _, qr_url = generer_qr_et_url(token)
    
    return render_template('etudiant/releve.html', 
                           etu=etu, insc=insc,
                           rows_s1=rows_s1, rs1=rs1, sem1=sem1,
                           rows_s2=rows_s2, rs2=rs2, sem2=sem2, ra=ra,
                           qr_url=qr_url, token=token)


@etudiant_bp.route('/releve/telecharger/<string:token>')
@login_required
@etudiant_requis
def telecharger_releve(token):
    etu    = get_etu()
    releve = ReleverNotes.query.filter_by(
        qr_code_token=token, etudiant_id=etu.id).first_or_404()
    chemin = os.path.join(current_app.config['UPLOAD_FOLDER'],
                          *releve.fichier_url.split('/')[1:])
    if not os.path.exists(chemin):
        abort(404)
    return send_file(chemin, as_attachment=True,
                     download_name=releve.nom_fichier or 'releve.pdf',
                     mimetype='application/pdf')


# ── Corrections ───────────────────────────────────────────────
@etudiant_bp.route('/corrections')
@login_required
@etudiant_requis
def corrections():
    etu  = get_etu()
    insc = etu.get_inscription_active()
    corrections_list = []
    if insc:
        from app.models.academic import Semestre
        # Fetch affectations for the entire current academic year instead of just one semester
        affs = AffectationEnseignement.query.join(Semestre).filter(
            AffectationEnseignement.section_id == insc.section_id,
            AffectationEnseignement.est_active == True,
            Semestre.annee_scolaire_id == insc.annee_scolaire_id
        ).all()
        
        for aff in affs:
            corrs = CorrectionExamen.query.filter_by(
                affectation_id=aff.id, est_publie=True
            ).order_by(CorrectionExamen.date_publication.desc()).all()
            if corrs:
                corrections_list.append({
                    'matiere': aff.matiere,
                    'section': aff.section,
                    'corrections': corrs,
                })
    return render_template('etudiant/corrections.html',
                           corrections_list=corrections_list)


@etudiant_bp.route('/corrections/telecharger/<int:corr_id>')
@login_required
@etudiant_requis
def telecharger_correction(corr_id):
    etu  = get_etu()
    corr = CorrectionExamen.query.get_or_404(corr_id)
    if not corr.est_publie:
        abort(404)
    aff = corr.affectation
    insc = Inscription.query.filter_by(
        etudiant_id=etu.id, section_id=aff.section_id, statut='actif'
    ).first()
    if not insc:
        abort(403)
    chemin = chemin_absolu_upload(corr.fichier_url)
    if not chemin or not os.path.exists(chemin):
        abort(404)
        
    nom = corr.nom_fichier_original
    if not nom:
        ext = corr.fichier_url.rsplit('.', 1)[-1] if '.' in corr.fichier_url else 'pdf'
        nom = f'correction.{ext}'
        
    return send_file(chemin, as_attachment=True, download_name=nom)


# Les routes pour espace_cours, devoirs, chat, etc. ont été déplacées vers espace_etudes/routes.py
