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
from app.models.program import AffectationEnseignement
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


@etudiant_bp.route('/chat/cours/<int:cours_id>')
@login_required
@etudiant_requis
def chat_cours(cours_id):
    cours = Cours.query.get_or_404(cours_id)
    conv = Conversation.query.filter_by(
        participant_a_id=current_user.id,
        participant_b_id=cours.publie_par,
        cours_id=cours.id,
        type='cours_etudiant_professeur'
    ).first()
    
    if not conv:
        conv = Conversation(
            type='cours_etudiant_professeur',
            participant_a_id=current_user.id,
            participant_a_role='etudiant',
            participant_b_id=cours.publie_par,
            cours_id=cours.id,
            sujet=f"Question sur le cours: {cours.titre}"
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


@etudiant_bp.route('/chat/message/<int:msg_id>/supprimer', methods=['POST'])
@login_required
@etudiant_requis
def supprimer_message(msg_id):
    try:
        msg = Message.query.get_or_404(msg_id)
        conv = msg.conversation
        if conv.participant_a_id != current_user.id:
            abort(403)
            
        data = request.get_json() or {}
        pour_tous = data.get('pour_tous', False)
        
        if msg.expediteur_utilisateur_id == current_user.id:
            if pour_tous:
                msg.supprime_par_expediteur = True
                msg.supprime_par_destinataire = True
            else:
                msg.supprime_par_expediteur = True
        else:
            msg.supprime_par_destinataire = True
            
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

# ── Espace Sujet (Google Classroom Style) ──────────────────────
@etudiant_bp.route('/sujet/<int:aff_id>')
@login_required
@etudiant_requis
def sujet(aff_id):
    etu = get_etu()
    insc = etu.get_inscription_active()
    aff = AffectationEnseignement.query.get_or_404(aff_id)
        
    cours_list = Cours.query.filter_by(affectation_id=aff_id, est_publie=True).order_by(Cours.ordre).all()
    devoirs_list = Devoir.query.filter_by(affectation_id=aff_id, est_publie=True).all()
    posts_list = PostProfesseur.query.filter_by(affectation_id=aff_id, est_publie=True).order_by(PostProfesseur.created_at.desc()).all()
    
    soumissions = {}
    for d in devoirs_list:
        soum = SoumissionDevoir.query.filter_by(devoir_id=d.id, etudiant_id=etu.id).first()
        soumissions[d.id] = soum
        
    return render_template('etudiant/sujet.html',
                           aff=aff, cours_list=cours_list, 
                           devoirs_list=devoirs_list, posts=posts_list,
                           soumissions=soumissions)

@etudiant_bp.route('/message_cours', methods=['POST'])
@login_required
@etudiant_requis
def message_cours():
    etu = get_etu()
    cours_id = request.form.get('cours_id', type=int)
    contenu = request.form.get('contenu')
    if not cours_id or not contenu:
        flash("Message invalide.", "danger")
        return redirect(request.referrer or url_for('etudiant.dashboard'))
        
    cours = Cours.query.get_or_404(cours_id)
    prof_id = cours.affectation.professeur_id
    
    conv = Conversation.query.filter_by(
        type='cours_etudiant_professeur',
        participant_a_id=etu.id,
        participant_a_role='etudiant',
        participant_b_id=prof_id,
        cours_id=cours.id
    ).first()
    
    if not conv:
        conv = Conversation(
            type='cours_etudiant_professeur',
            participant_a_id=etu.id,
            participant_a_role='etudiant',
            participant_b_id=prof_id,
            sujet=f"Question sur le cours: {cours.titre}",
            matiere_id=cours.affectation.matiere_id,
            etudiant_concerne_id=etu.id,
            cours_id=cours.id
        )
        db.session.add(conv)
        db.session.flush()
        
    msg = Message(
        conversation_id=conv.id,
        expediteur_id=current_user.id,
        contenu=contenu
    )
    db.session.add(msg)
    conv.date_dernier_message = datetime.now(timezone.utc)
    
    # Notify prof
    notifier_message(
        db, current_user.id, cours.affectation.professeur.utilisateur.id, 
        conv.id, f"Question sur {cours.titre}"
    )
    
    db.session.commit()
    flash("Votre message a été envoyé au professeur.", "success")
    return redirect(request.referrer or url_for('etudiant.sujet', aff_id=cours.affectation_id))

# ── Messagerie Privée (Google Classroom Style) ──────────────────────
@etudiant_bp.route('/messages', defaults={'conv_id': None})
@etudiant_bp.route('/messages/<int:conv_id>')
@login_required
@etudiant_requis
def messages(conv_id):
    etu = get_etu()
    
    # Fetch all conversations for this student
    conversations = Conversation.query.filter_by(
        participant_a_id=etu.id,
        participant_a_role='etudiant'
    ).order_by(Conversation.date_dernier_message.desc()).all()
    
    active_conv = None
    if conv_id:
        active_conv = Conversation.query.get_or_404(conv_id)
        if active_conv.participant_a_id != etu.id:
            abort(403)
        for msg in active_conv.messages:
            if msg.expediteur_id != current_user.id and not msg.est_lu:
                msg.est_lu = True
                msg.date_lecture = datetime.now(timezone.utc)
        db.session.commit()
    elif conversations:
        active_conv = conversations[0]
        
    return render_template('etudiant/messages.html', 
                           conversations=conversations, 
                           active_conv=active_conv)

@etudiant_bp.route('/envoyer_message_conv/<int:conv_id>', methods=['POST'])
@login_required
@etudiant_requis
def envoyer_message_conv(conv_id):
    etu = get_etu()
    conv = Conversation.query.get_or_404(conv_id)
    if conv.participant_a_id != etu.id:
        abort(403)
        
    contenu = request.form.get('contenu')
    if contenu:
        msg = Message(
            conversation_id=conv.id,
            expediteur_id=current_user.id,
            contenu=contenu
        )
        db.session.add(msg)
        conv.date_dernier_message = datetime.now(timezone.utc)
        
        # Notify prof (participant_b_id is prof id)
        # We need to get the Utilisateur id of the prof
        from app.models.profiles import Professeur
        prof = Professeur.query.get(conv.participant_b_id)
        
        from app.services.notif_service import notifier_message
        notifier_message(db, current_user.id, prof.utilisateur.id, conv.id, "Nouveau message de l'étudiant")
        db.session.commit()
        
    return redirect(url_for('etudiant.messages', conv_id=conv.id))
