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
from app.utils.helpers import sauvegarder_fichier
from app.models.profiles import Etudiant
from app.models.program import AffectationEnseignement, Inscription
from app.models.academic import AnneeScolaire, Semestre
from app.models.evaluation import Note, ResultatSemestre, ResultatAnnuel, ReleverNotes, CorrectionExamen
from app.models.pedagogy import Cours, Devoir, SoumissionDevoir, PostProfesseur, CommentairePost
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
    posts = []
    if insc:
        affs = AffectationEnseignement.query.filter_by(
            section_id=insc.section_id, semestre_id=insc.semestre_courant,
            est_active=True).all()
        aff_ids = [a.id for a in affs]
        posts = PostProfesseur.query.filter(
            PostProfesseur.affectation_id.in_(aff_ids),
            PostProfesseur.est_publie == True
        ).order_by(PostProfesseur.created_at.desc()).limit(5).all()
    return render_template('etudiant/dashboard.html',
                           etu=etu, insc=insc, notifs_count=notifs_count, posts=posts)


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
    releves = ReleverNotes.query.filter_by(etudiant_id=etu.id).all()
    return render_template('etudiant/releve.html', etu=etu, releves=releves, insc=insc)


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
        affs = AffectationEnseignement.query.filter_by(
            section_id=insc.section_id, est_active=True).all()
        for aff in affs:
            corrs = CorrectionExamen.query.filter_by(
                affectation_id=aff.id, est_publie=True).all()
            if corrs:
                corrections_list.append({'matiere': aff.matiere, 'corrections': corrs})
    return render_template('etudiant/corrections.html',
                           corrections_list=corrections_list)


@etudiant_bp.route('/corrections/telecharger/<int:corr_id>')
@login_required
@etudiant_requis
def telecharger_correction(corr_id):
    corr   = CorrectionExamen.query.get_or_404(corr_id)
    chemin = os.path.join(current_app.config['UPLOAD_FOLDER'],
                          *corr.fichier_url.split('/')[1:])
    if not os.path.exists(chemin):
        abort(404)
    return send_file(chemin, as_attachment=True,
                     download_name=corr.nom_fichier_original or 'correction.pdf')


# ── Espace Cours ──────────────────────────────────────────────
@etudiant_bp.route('/cours')
@login_required
@etudiant_requis
def espace_cours():
    etu  = get_etu()
    insc = etu.get_inscription_active()
    annee_id = request.args.get('annee_id', type=int)
    sem_num  = request.args.get('sem', 1, type=int)
    annees   = AnneeScolaire.query.order_by(AnneeScolaire.annee_debut.desc()).all()
    cours_par_matiere = []
    if insc and annee_id:
        sem = Semestre.query.filter_by(
            annee_scolaire_id=annee_id, numero=sem_num).first()
        if sem:
            affs = AffectationEnseignement.query.filter_by(
                section_id=insc.section_id, semestre_id=sem.id).all()
            for aff in affs:
                cours_list = Cours.query.filter_by(
                    affectation_id=aff.id, est_publie=True).all()
                cours_par_matiere.append({
                    'matiere'    : aff.matiere,
                    'professeur' : aff.professeur,
                    'affectation': aff,
                    'cours'      : cours_list,
                })
    return render_template('etudiant/espace_cours.html',
                           etu=etu, insc=insc, annees=annees,
                           cours_par_matiere=cours_par_matiere,
                           annee_id=annee_id, sem_num=sem_num)


@etudiant_bp.route('/cours/telecharger/<int:cours_id>')
@login_required
@etudiant_requis
def telecharger_cours(cours_id):
    cours  = Cours.query.get_or_404(cours_id)
    chemin = os.path.join(current_app.config['UPLOAD_FOLDER'],
                          *cours.fichier_url.split('/')[1:])
    if not os.path.exists(chemin):
        abort(404)
    return send_file(chemin, as_attachment=True,
                     download_name=cours.nom_fichier_original or cours.titre)


# ── Devoirs ───────────────────────────────────────────────────
@etudiant_bp.route('/devoirs')
@login_required
@etudiant_requis
def devoirs():
    etu  = get_etu()
    insc = etu.get_inscription_active()
    devoirs_list = []
    if insc:
        affs = AffectationEnseignement.query.filter_by(
            section_id=insc.section_id, est_active=True).all()
        for aff in affs:
            devs = Devoir.query.filter_by(
                affectation_id=aff.id, est_publie=True).all()
            for dev in devs:
                soum = SoumissionDevoir.query.filter_by(
                    devoir_id=dev.id, etudiant_id=etu.id).first()
                devoirs_list.append({'devoir': dev, 'soumission': soum,
                                     'matiere': aff.matiere})
    return render_template('etudiant/devoirs.html', devoirs=devoirs_list)


@etudiant_bp.route('/devoirs/soumettre/<int:dev_id>', methods=['POST'])
@login_required
@etudiant_requis
def soumettre_devoir(dev_id):
    etu    = get_etu()
    dev    = Devoir.query.get_or_404(dev_id)
    fichier = request.files.get('fichier')
    try:
        chemin = sauvegarder_fichier(fichier, 'soumissions')
        ext    = fichier.filename.rsplit('.', 1)[-1].lower()
        tf     = 'pdf' if ext == 'pdf' else 'word' if ext in ('doc','docx') else 'autre'
        retard = datetime.now(timezone.utc) > dev.date_limite_soumission.replace(tzinfo=timezone.utc)
        existing = SoumissionDevoir.query.filter_by(
            devoir_id=dev_id, etudiant_id=etu.id).first()
        if existing:
            existing.fichier_url = chemin
            existing.type_fichier = tf
            existing.date_soumission = datetime.now(timezone.utc)
            existing.est_en_retard = retard
        else:
            soum = SoumissionDevoir(
                devoir_id=dev_id, etudiant_id=etu.id,
                fichier_url=chemin, type_fichier=tf,
                nom_fichier_original=fichier.filename,
                est_en_retard=retard,
            )
            db.session.add(soum)
        db.session.commit()
        flash('Devoir soumis avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('etudiant.devoirs'))


# ── Chat ──────────────────────────────────────────────────────
@etudiant_bp.route('/chat')
@login_required
@etudiant_requis
def chat():
    etu  = get_etu()
    insc = etu.get_inscription_active()
    convs = Conversation.query.filter_by(
        participant_a_id=current_user.id, participant_a_role='etudiant').all()
    return render_template('etudiant/chat.html', convs=convs, insc=insc)


@etudiant_bp.route('/chat/nouvelle/<int:prof_user_id>')
@login_required
@etudiant_requis
def nouvelle_conversation(prof_user_id):
    conv = Conversation.query.filter_by(
        participant_a_id=current_user.id,
        participant_b_id=prof_user_id,
        type='etudiant_professeur'
    ).first()
    if not conv:
        conv = Conversation(
            type='etudiant_professeur',
            participant_a_id=current_user.id,
            participant_a_role='etudiant',
            participant_b_id=prof_user_id,
        )
        db.session.add(conv)
        db.session.commit()
    return redirect(url_for('etudiant.conversation_detail', conv_id=conv.id))


@etudiant_bp.route('/chat/<int:conv_id>')
@login_required
@etudiant_requis
def conversation_detail(conv_id):
    conv = Conversation.query.get_or_404(conv_id)
    if conv.participant_a_id != current_user.id:
        abort(403)
    msgs = conv.messages.filter_by(supprime_par_expediteur=False).all()
    return render_template('etudiant/conversation.html', conv=conv, msgs=msgs)


@etudiant_bp.route('/chat/envoyer', methods=['POST'])
@login_required
@etudiant_requis
def envoyer_message():
    try:
        conv_id = int(request.form['conv_id'])
        contenu = request.form['contenu'].strip()
        conv    = Conversation.query.get_or_404(conv_id)
        if conv.participant_a_id != current_user.id:
            abort(403)
        msg = Message(
            conversation_id=conv_id,
            expediteur_utilisateur_id=current_user.id,
            expediteur_role='etudiant',
            contenu=contenu,
        )
        db.session.add(msg)
        db.session.commit()
        notifier_message(conv_id, current_user.id,
                         conv.participant_b_id, 'professeur')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
