# =============================================================
#  EduNova — blueprints/professeur/routes.py
# =============================================================
from datetime import datetime, timezone
from flask import (render_template, redirect, url_for, request,
                   flash, abort, jsonify)
from flask_login import login_required, current_user
from app.blueprints.professeur import prof_bp
from app.extensions import db
from app.utils.decorators import professeur_requis
from app.utils.helpers import sauvegarder_fichier
from app.models.profiles import Professeur
from app.models.program import AffectationEnseignement, Inscription
from app.models.evaluation import Note, CorrectionExamen
from app.models.presence import Seance, Presence
from app.models.pedagogy import Cours, Devoir, PostProfesseur
from app.models.communication import Conversation, Message
from app.services.note_service import sauvegarder_note
from app.services.notif_service import notifier_message, notifier_note_publiee


def get_prof() -> Professeur:
    return current_user.professeur


@prof_bp.route('/dashboard')
@login_required
@professeur_requis
def dashboard():
    prof = get_prof()
    affs = AffectationEnseignement.query.filter_by(
        professeur_id=prof.id, est_active=True).all()
    # Notifications non lues
    from app.models.communication import Notification
    notifs_count = Notification.query.filter_by(
        destinataire_id=current_user.id, est_lu=False).count()
    return render_template('professeur/dashboard.html',
                           prof=prof, affs=affs, notifs_count=notifs_count)


# ── Notes ─────────────────────────────────────────────────────
@prof_bp.route('/notes')
@login_required
@professeur_requis
def notes():
    prof = get_prof()
    affs = AffectationEnseignement.query.filter_by(
        professeur_id=prof.id, est_active=True).all()
    aff_id = request.args.get('aff_id', type=int)
    etudiants_notes = []
    aff_selectionnee = None
    if aff_id:
        aff_selectionnee = AffectationEnseignement.query.get_or_404(aff_id)
        if aff_selectionnee.professeur_id != prof.id:
            abort(403)
        inscs = Inscription.query.filter_by(
            section_id=aff_selectionnee.section_id, statut='actif').all()
        q = request.args.get('q', '').strip()
        for insc in inscs:
            etu = insc.etudiant
            if q and q.lower() not in etu.utilisateur.username.lower():
                continue
            note = Note.query.filter_by(
                etudiant_id=etu.id, affectation_id=aff_id).first()
            etudiants_notes.append({'etudiant': etu, 'note': note})
    return render_template('professeur/notes.html',
                           affs=affs, aff_selectionnee=aff_selectionnee,
                           etudiants_notes=etudiants_notes)


@prof_bp.route('/notes/sauvegarder', methods=['POST'])
@login_required
@professeur_requis
def sauvegarder_notes():
    prof   = get_prof()
    aff_id = int(request.form['aff_id'])
    aff    = AffectationEnseignement.query.get_or_404(aff_id)
    if aff.professeur_id != prof.id:
        abort(403)
    try:
        etu_ids = request.form.getlist('etudiant_id')
        for etu_id in etu_ids:
            etu_id = int(etu_id)
            d1  = request.form.get(f'd1_{etu_id}') or None
            d2  = request.form.get(f'd2_{etu_id}') or None
            ec  = request.form.get(f'ec_{etu_id}') or None
            ex  = request.form.get(f'ex_{etu_id}') or None
            ok  = sauvegarder_note(etu_id, aff_id, prof.id, d1, d2, ec, ex)
            if ok:
                notifier_note_publiee(etu_id, aff.matiere.nom)
        flash('Notes enregistrées avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('professeur.notes', aff_id=aff_id))


@prof_bp.route('/notes/ajax_save', methods=['POST'])
@login_required
@professeur_requis
def ajax_save_note():
    prof = get_prof()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    aff_id = int(data.get('aff_id', 0))
    etu_id = int(data.get('etu_id', 0))
    aff = AffectationEnseignement.query.get_or_404(aff_id)
    
    if aff.professeur_id != prof.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        # Convert empty strings to None
        d1 = data.get('d1') if data.get('d1') != '' else None
        d2 = data.get('d2') if data.get('d2') != '' else None
        ec = data.get('ec') if data.get('ec') != '' else None
        ex = data.get('ex') if data.get('ex') != '' else None
        
        ok = sauvegarder_note(etu_id, aff_id, prof.id, d1, d2, ec, ex)
        if ok:
            notifier_note_publiee(etu_id, aff.matiere.nom)
            
        return jsonify({'success': True, 'message': 'Saved'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ── Présences ─────────────────────────────────────────────────
@prof_bp.route('/presences')
@login_required
@professeur_requis
def presences():
    prof = get_prof()
    affs = AffectationEnseignement.query.filter_by(
        professeur_id=prof.id, est_active=True).all()
    aff_id = request.args.get('aff_id', type=int)
    etudiants_liste = []
    aff_sel = None
    if aff_id:
        aff_sel = AffectationEnseignement.query.get_or_404(aff_id)
        if aff_sel.professeur_id != prof.id:
            abort(403)
        q = request.args.get('q', '').strip()
        inscs = Inscription.query.filter_by(
            section_id=aff_sel.section_id, statut='actif').all()
        for insc in inscs:
            etu = insc.etudiant
            if q and q.lower() not in etu.utilisateur.username.lower():
                continue
            etudiants_liste.append(etu)
    return render_template('professeur/presences.html',
                           affs=affs, aff_selectionnee=aff_sel,
                           etudiants=etudiants_liste)


@prof_bp.route('/presences/enregistrer', methods=['POST'])
@login_required
@professeur_requis
def enregistrer_presences():
    prof   = get_prof()
    aff_id = int(request.form['aff_id'])
    aff    = AffectationEnseignement.query.get_or_404(aff_id)
    if aff.professeur_id != prof.id:
        abort(403)
    try:
        date_s   = datetime.strptime(request.form['date_seance'], '%Y-%m-%d').date()
        h_debut  = datetime.strptime(request.form['heure_debut'], '%H:%M').time()
        h_fin    = datetime.strptime(request.form['heure_fin'],   '%H:%M').time()
        type_s   = request.form.get('type_seance', 'cours')
        etu_ids  = request.form.getlist('etudiant_id')
        data     = []
        for eid in etu_ids:
            statut = request.form.get(f'statut_{eid}', 'present')
            data.append({'etudiant_id': int(eid), 'statut': statut})
        from app.models.presence import CompteurAbsences
        from app.services.notif_service import notifier_absence
        
        seance = Seance(affectation_id=aff_id, date_seance=date_s,
                        heure_debut=h_debut, heure_fin=h_fin, type_seance=type_s)
        db.session.add(seance)
        db.session.flush()
        
        for item in data:
            eid    = item['etudiant_id']
            statut = item['statut']
            pres   = Presence(seance_id=seance.id, etudiant_id=eid,
                               statut=statut, enregistre_par=prof.id)
            db.session.add(pres)
            
            insc = Inscription.query.filter_by(etudiant_id=eid, statut='actif').first()
            if insc and statut == 'absent':
                cpt = CompteurAbsences.query.filter_by(
                    etudiant_id=eid, inscription_id=insc.id,
                    semestre_id=aff.semestre_id).first()
                if not cpt:
                    cpt = CompteurAbsences(etudiant_id=eid,
                                           inscription_id=insc.id,
                                           semestre_id=aff.semestre_id)
                    db.session.add(cpt)
                    db.session.flush()
                cpt.total_seances += 1
                cpt.incrementer_absence(False)
                db.session.flush()
                notifier_absence(eid, seance.id)
        db.session.commit()
        flash('Présences enregistrées.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('professeur.presences', aff_id=aff_id))


# ── Corrections ───────────────────────────────────────────────
@prof_bp.route('/corrections')
@login_required
@professeur_requis
def corrections():
    prof = get_prof()
    affs = AffectationEnseignement.query.filter_by(
        professeur_id=prof.id, est_active=True).all()
    corrections_list = CorrectionExamen.query.filter_by(publie_par=prof.id).all()
    return render_template('professeur/corrections.html',
                           affs=affs, corrections=corrections_list)


@prof_bp.route('/corrections/ajouter', methods=['POST'])
@login_required
@professeur_requis
def ajouter_correction():
    prof = get_prof()
    try:
        aff_id       = int(request.form['aff_id'])
        type_eval    = request.form['type_evaluation']
        titre        = request.form['titre'].strip()
        fichier      = request.files.get('fichier')
        chemin       = sauvegarder_fichier(fichier, 'corrections')
        ext          = fichier.filename.rsplit('.', 1)[-1].lower() if fichier else 'autre'
        type_fichier = 'pdf' if ext == 'pdf' else ('word' if ext in ('doc','docx') else 'image')

        # Un seul par type d'évaluation et affectation
        existing = CorrectionExamen.query.filter_by(
            affectation_id=aff_id, type_evaluation=type_eval).first()
        if existing:
            existing.fichier_url  = chemin
            existing.type_fichier = type_fichier
            existing.nom_fichier_original = fichier.filename
            existing.est_publie   = True
            existing.date_publication = datetime.now(timezone.utc)
        else:
            corr = CorrectionExamen(
                affectation_id=aff_id, type_evaluation=type_eval,
                titre=titre, fichier_url=chemin, type_fichier=type_fichier,
                nom_fichier_original=fichier.filename,
                est_publie=True, date_publication=datetime.now(timezone.utc),
                publie_par=prof.id,
            )
            db.session.add(corr)
        db.session.commit()
        flash('Correction publiée.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('professeur.corrections'))


# ── Cours ─────────────────────────────────────────────────────
@prof_bp.route('/cours')
@login_required
@professeur_requis
def cours():
    prof = get_prof()
    affs = AffectationEnseignement.query.filter_by(
        professeur_id=prof.id, est_active=True).all()
    aff_id = request.args.get('aff_id', type=int)
    cours_list = []
    aff_sel    = None
    if aff_id:
        aff_sel    = AffectationEnseignement.query.get_or_404(aff_id)
        cours_list = Cours.query.filter_by(affectation_id=aff_id)\
                         .order_by(Cours.ordre).all()
    return render_template('professeur/cours.html',
                           affs=affs, aff_selectionnee=aff_sel, cours_list=cours_list)


@prof_bp.route('/cours/ajouter', methods=['POST'])
@login_required
@professeur_requis
def ajouter_cours():
    prof = get_prof()
    try:
        aff_id  = int(request.form['aff_id'])
        titre   = request.form['titre'].strip()
        fichier = request.files.get('fichier')
        chemin  = sauvegarder_fichier(fichier, 'cours') if fichier else None
        ext     = fichier.filename.rsplit('.', 1)[-1].lower() if fichier else ''
        type_c  = 'pdf' if ext == 'pdf' else ('video' if ext in ('mp4','avi') else
                  'audio' if ext in ('mp3',) else 'image' if ext in ('jpg','jpeg','png') else 'pdf')
        c = Cours(
            affectation_id=aff_id, titre=titre, type_contenu=type_c,
            fichier_url=chemin, nom_fichier_original=fichier.filename if fichier else None,
            est_publie=True, date_publication=datetime.now(timezone.utc),
            publie_par=prof.id,
        )
        db.session.add(c)
        db.session.commit()
        flash('Cours publié.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('professeur.cours', aff_id=request.form.get('aff_id')))


# ── Devoirs ───────────────────────────────────────────────────
@prof_bp.route('/devoirs')
@login_required
@professeur_requis
def devoirs():
    prof       = get_prof()
    affs       = AffectationEnseignement.query.filter_by(
        professeur_id=prof.id, est_active=True).all()
    dev_list   = Devoir.query.filter_by(publie_par=prof.id).all()
    return render_template('professeur/devoirs.html', affs=affs, devoirs=dev_list)


@prof_bp.route('/devoirs/ajouter', methods=['POST'])
@login_required
@professeur_requis
def ajouter_devoir():
    prof = get_prof()
    try:
        aff_id  = int(request.form['aff_id'])
        titre   = request.form['titre'].strip()
        desc    = request.form['description'].strip()
        limite  = datetime.strptime(request.form['date_limite'], '%Y-%m-%dT%H:%M')
        fichier = request.files.get('fichier')
        chemin  = sauvegarder_fichier(fichier, 'devoirs') if fichier else None
        dev = Devoir(
            affectation_id=aff_id, titre=titre, description=desc,
            fichier_url=chemin, date_publication=datetime.now(timezone.utc),
            date_limite_soumission=limite, est_publie=True, publie_par=prof.id,
        )
        db.session.add(dev)
        db.session.commit()
        flash('Devoir publié.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('professeur.devoirs'))


# ── Chat ──────────────────────────────────────────────────────
@prof_bp.route('/chat')
@login_required
@professeur_requis
def chat():
    convs = Conversation.query.filter_by(participant_b_id=current_user.id).all()
    etudiants_convs = [c for c in convs if c.participant_a_role == 'etudiant']
    parents_convs   = [c for c in convs if c.participant_a_role == 'parent']
    return render_template('professeur/chat.html',
                           etudiants_convs=etudiants_convs,
                           parents_convs=parents_convs)


@prof_bp.route('/chat/conversation/<int:conv_id>')
@login_required
@professeur_requis
def conversation(conv_id):
    conv = Conversation.query.get_or_404(conv_id)
    if conv.participant_b_id != current_user.id:
        abort(403)
    msgs = conv.messages.filter_by(supprime_par_destinataire=False).all()
    return render_template('professeur/conversation.html', conv=conv, msgs=msgs)


@prof_bp.route('/chat/envoyer', methods=['POST'])
@login_required
@professeur_requis
def envoyer_message():
    try:
        conv_id = int(request.form['conv_id'])
        contenu = request.form['contenu'].strip()
        conv    = Conversation.query.get_or_404(conv_id)
        if conv.participant_b_id != current_user.id:
            abort(403)
        msg = Message(
            conversation_id=conv_id,
            expediteur_utilisateur_id=current_user.id,
            expediteur_role='professeur',
            contenu=contenu,
        )
        db.session.add(msg)
        db.session.commit()
        notifier_message(conv_id, current_user.id,
                         conv.participant_a_id, conv.participant_a_role)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# ── Posts ─────────────────────────────────────────────────────
@prof_bp.route('/posts')
@login_required
@professeur_requis
def posts():
    prof      = get_prof()
    affs      = AffectationEnseignement.query.filter_by(
        professeur_id=prof.id, est_active=True).all()
    posts_list = PostProfesseur.query.filter_by(professeur_id=prof.id)\
                     .order_by(PostProfesseur.created_at.desc()).all()
    return render_template('professeur/posts.html', affs=affs, posts=posts_list)


@prof_bp.route('/posts/ajouter', methods=['POST'])
@login_required
@professeur_requis
def ajouter_post():
    prof = get_prof()
    try:
        contenu     = request.form['contenu'].strip()
        type_public = request.form.get('type_public', 'tous')
        aff_id      = request.form.get('aff_id', type=int)
        post = PostProfesseur(
            professeur_id=prof.id, contenu=contenu,
            type_public=type_public,
            affectation_id=aff_id if type_public == 'section' else None,
        )
        db.session.add(post)
        db.session.commit()
        flash('Post publié.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('professeur.posts'))
