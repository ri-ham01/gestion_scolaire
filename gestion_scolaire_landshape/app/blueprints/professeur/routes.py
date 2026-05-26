# =============================================================
#  EduNova — blueprints/professeur/routes.py
# =============================================================
from datetime import datetime, timezone
from flask import (render_template, redirect, url_for, request,
                   flash, abort, jsonify, send_file)
import os
from flask_login import login_required, current_user
from app.blueprints.professeur import prof_bp
from app.extensions import db
from app.utils.decorators import professeur_requis
from app.utils.helpers import (sauvegarder_fichier, allowed_file,
                               type_fichier_pedagogique, chemin_absolu_upload)
from app.models.profiles import Professeur
from app.models.program import AffectationEnseignement, Inscription
from app.models.evaluation import Note, CorrectionExamen
from app.models.presence import Seance, Presence
from app.models.pedagogy import Cours, Devoir, PostProfesseur
from app.models.communication import Conversation, Message
from app.services.note_service import sauvegarder_note
from app.services.notif_service import (notifier_message, notifier_note_publiee,
                                        notifier_correction_publiee)


def get_prof() -> Professeur:
    return current_user.professeur


@prof_bp.route('/dashboard')
@login_required
@professeur_requis
def dashboard():
    prof = get_prof()
    affs = AffectationEnseignement.query.filter_by(
        professeur_id=prof.id, est_active=True).all()
    total_students = sum(aff.section.inscriptions.count() for aff in affs)
    # Notifications non lues
    from app.models.communication import Notification
    notifs_count = Notification.query.filter_by(
        destinataire_id=current_user.id, est_lu=False).count()
    return render_template('professeur/dashboard.html',
                           prof=prof, affs=affs, notifs_count=notifs_count,
                           total_students=total_students)

@prof_bp.route('/mes-etudiants')
@login_required
@professeur_requis
def mes_etudiants():
    prof = get_prof()
    affs = AffectationEnseignement.query.filter_by(
        professeur_id=prof.id, est_active=True).all()
    aff_id = request.args.get('aff_id', type=int)
    etudiants_liste = []
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
            if q and q.lower() not in etu.utilisateur.username.lower() and q.lower() not in etu.nom.lower() and q.lower() not in etu.prenom.lower():
                continue
            etudiants_liste.append({'etudiant': etu, 'inscription': insc})
    return render_template('professeur/mes_etudiants.html',
                           affs=affs, aff_selectionnee=aff_selectionnee,
                           etudiants=etudiants_liste, q=request.args.get('q', ''))

# ── Notes ─────────────────────────────────────────────────────
@prof_bp.route('/notes')
@login_required
@professeur_requis
def notes():
    prof = get_prof()
    affs = AffectationEnseignement.query.filter_by(
        professeur_id=prof.id, est_active=True).all()
        
    hierarchie = {}
    spec_dict = {}
    mat_dict = {}
    
    for aff in affs:
        spec = aff.section.specialite
        mat = aff.matiere
        spec_dict[spec.id] = spec
        mat_dict[mat.id] = mat
        
        if spec.id not in hierarchie:
            hierarchie[spec.id] = {}
        if mat.id not in hierarchie[spec.id]:
            hierarchie[spec.id][mat.id] = []
        hierarchie[spec.id][mat.id].append(aff)
        
    spec_sel_id = request.args.get('spec_id', type=int)
    mat_sel_id = request.args.get('mat_id', type=int)
    q = request.args.get('q', '').strip()
    
    classes_notes = []
    
    if spec_sel_id and mat_sel_id and spec_sel_id in hierarchie and mat_sel_id in hierarchie[spec_sel_id]:
        for aff in hierarchie[spec_sel_id][mat_sel_id]:
            inscs = Inscription.query.filter_by(section_id=aff.section_id, statut='actif').all()
            etudiants_notes = []
            for insc in inscs:
                etu = insc.etudiant
                # Advanced search: check username, nom, prenom
                if q:
                    search_str = f"{etu.utilisateur.username} {etu.nom} {etu.prenom}".lower()
                    if q.lower() not in search_str:
                        continue
                note = Note.query.filter_by(etudiant_id=etu.id, affectation_id=aff.id).first()
                etudiants_notes.append({'etudiant': etu, 'note': note})
            classes_notes.append({
                'affectation': aff,
                'section': aff.section,
                'etudiants_notes': etudiants_notes
            })
            
    return render_template('professeur/notes.html',
                           hierarchie=hierarchie,
                           spec_dict=spec_dict,
                           mat_dict=mat_dict,
                           spec_sel_id=spec_sel_id,
                           mat_sel_id=mat_sel_id,
                           classes_notes=classes_notes,
                           q=q)


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
        
    hierarchie = {}
    spec_dict = {}
    mat_dict = {}
    
    for aff in affs:
        spec = aff.section.specialite
        mat = aff.matiere
        spec_dict[spec.id] = spec
        mat_dict[mat.id] = mat
        
        if spec.id not in hierarchie:
            hierarchie[spec.id] = {}
        if mat.id not in hierarchie[spec.id]:
            hierarchie[spec.id][mat.id] = []
        hierarchie[spec.id][mat.id].append(aff)
        
    spec_sel_id = request.args.get('spec_id', type=int)
    mat_sel_id = request.args.get('mat_id', type=int)
    q = request.args.get('q', '').strip()
    
    classes_etudiants = []
    
    if spec_sel_id and mat_sel_id and spec_sel_id in hierarchie and mat_sel_id in hierarchie[spec_sel_id]:
        for aff in hierarchie[spec_sel_id][mat_sel_id]:
            inscs = Inscription.query.filter_by(section_id=aff.section_id, statut='actif').all()
            etudiants_liste = []
            for insc in inscs:
                etu = insc.etudiant
                if q:
                    search_str = f"{etu.utilisateur.username} {etu.nom} {etu.prenom}".lower()
                    if q.lower() not in search_str:
                        continue
                etudiants_liste.append(etu)
            classes_etudiants.append({
                'affectation': aff,
                'section': aff.section,
                'etudiants': etudiants_liste
            })
            
    return render_template('professeur/presences.html',
                           hierarchie=hierarchie,
                           spec_dict=spec_dict,
                           mat_dict=mat_dict,
                           spec_sel_id=spec_sel_id,
                           mat_sel_id=mat_sel_id,
                           classes_etudiants=classes_etudiants,
                           q=q)


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
    corrections_list = (
        CorrectionExamen.query
        .join(AffectationEnseignement,
              CorrectionExamen.affectation_id == AffectationEnseignement.id)
        .filter(AffectationEnseignement.professeur_id == prof.id)
        .order_by(CorrectionExamen.date_publication.desc(),
                  CorrectionExamen.updated_at.desc())
        .all()
    )
    return render_template('professeur/corrections.html',
                           affs=affs, corrections=corrections_list)


@prof_bp.route('/corrections/ajouter', methods=['POST'])
@login_required
@professeur_requis
def ajouter_correction():
    prof = get_prof()
    try:
        aff_raw = request.form.get('aff_id') or request.form.get('affectation_id')
        if not aff_raw:
            raise ValueError('Veuillez sélectionner une matière et une section.')
        aff_id    = int(aff_raw)
        type_eval = request.form['type_evaluation']
        titre     = request.form['titre'].strip()
        fichier   = request.files.get('fichier')

        aff = AffectationEnseignement.query.get_or_404(aff_id)
        if aff.professeur_id != prof.id:
            abort(403)

        if not fichier or fichier.filename == '':
            raise ValueError('Veuillez sélectionner un fichier (PDF, Word ou image).')
        if not allowed_file(fichier.filename, 'all'):
            raise ValueError('Type de fichier non autorisé. Utilisez PDF, Word (.doc/.docx) ou image.')

        chemin = sauvegarder_fichier(fichier, 'corrections')
        if not chemin:
            raise ValueError('Échec de l\'enregistrement du fichier.')

        type_fichier = type_fichier_pedagogique(fichier.filename)

        existing = CorrectionExamen.query.filter_by(
            affectation_id=aff_id, type_evaluation=type_eval).first()
        if existing:
            existing.titre = titre
            existing.fichier_url = chemin
            existing.type_fichier = type_fichier
            existing.nom_fichier_original = fichier.filename
            existing.est_publie = True
            existing.date_publication = datetime.now(timezone.utc)
            corr = existing
        else:
            corr = CorrectionExamen(
                affectation_id=aff_id, type_evaluation=type_eval,
                titre=titre, fichier_url=chemin, type_fichier=type_fichier,
                nom_fichier_original=fichier.filename,
                est_publie=True, date_publication=datetime.now(timezone.utc),
                publie_par=prof.id,
            )
            db.session.add(corr)
        db.session.flush()
        notifier_correction_publiee(aff_id, aff.matiere.nom, corr.id)
        db.session.commit()
        flash('Correction publiée et accessible à tous les étudiants de cette classe.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('professeur.corrections'))


@prof_bp.route('/corrections/telecharger/<int:corr_id>')
@login_required
@professeur_requis
def telecharger_correction(corr_id):
    prof = get_prof()
    corr = CorrectionExamen.query.get_or_404(corr_id)
    if corr.publie_par != prof.id:
        abort(403)
    chemin = chemin_absolu_upload(corr.fichier_url)
    if not chemin or not os.path.exists(chemin):
        abort(404)
        
    nom = corr.nom_fichier_original
    if not nom:
        ext = corr.fichier_url.rsplit('.', 1)[-1] if '.' in corr.fichier_url else 'pdf'
        nom = f'correction.{ext}'
        
    return send_file(chemin, as_attachment=True, download_name=nom)


# ── Les routes pour les cours et les devoirs ont été déplacées vers l'Espace Études ──


# ── Communication Parents ───────────────────────────────────────
@prof_bp.route('/parents')
@login_required
@professeur_requis
def parents():
    prof = current_user.professeur
    affs = AffectationEnseignement.query.filter_by(
        professeur_id=prof.id, est_active=True).all()
        
    hierarchie = {}
    spec_dict = {}
    mat_dict = {}
    
    for aff in affs:
        spec = aff.section.specialite
        mat = aff.matiere
        spec_dict[spec.id] = spec
        mat_dict[mat.id] = mat
        
        if spec.id not in hierarchie:
            hierarchie[spec.id] = {}
        if mat.id not in hierarchie[spec.id]:
            hierarchie[spec.id][mat.id] = []
        hierarchie[spec.id][mat.id].append(aff)
        
    spec_sel_id = request.args.get('spec_id', type=int)
    mat_sel_id = request.args.get('mat_id', type=int)
    q = request.args.get('q', '').strip()
    
    classes_parents = []
    
    if spec_sel_id and mat_sel_id and spec_sel_id in hierarchie and mat_sel_id in hierarchie[spec_sel_id]:
        for aff in hierarchie[spec_sel_id][mat_sel_id]:
            inscs = Inscription.query.filter_by(section_id=aff.section_id, statut='actif').all()
            parents_list = []
            for insc in inscs:
                etu = insc.etudiant
                if q:
                    search_str = f"{etu.utilisateur.username} {etu.nom} {etu.prenom}".lower()
                    if q.lower() not in search_str:
                        continue
                for pe in etu.parents_link:
                    parents_list.append({
                        'parent': pe.parent,
                        'etudiant': etu
                    })
            classes_parents.append({
                'affectation': aff,
                'section': aff.section,
                'parents': parents_list
            })
            
    # Keep track of active conversations
    convs = Conversation.query.filter_by(participant_b_id=current_user.id).all()
    parents_convs = [c for c in convs if c.participant_a_role == 'parent']

    return render_template('professeur/parents.html',
                           hierarchie=hierarchie,
                           spec_dict=spec_dict,
                           mat_dict=mat_dict,
                           spec_sel_id=spec_sel_id,
                           mat_sel_id=mat_sel_id,
                           classes_parents=classes_parents,
                           q=q,
                           parents_convs=parents_convs)


@prof_bp.route('/chat/nouveau_parent', methods=['POST'])
@login_required
@professeur_requis
def nouveau_chat_parent():
    parent_id = request.form.get('parent_id', type=int)
    if not parent_id:
        flash('Veuillez sélectionner un parent.', 'danger')
        return redirect(url_for('professeur.chat'))
        
    from app.models.profiles import Parent
    parent = Parent.query.get_or_404(parent_id)
    
    # Check if conversation already exists
    conv = Conversation.query.filter_by(
        participant_a_id=parent.utilisateur_id,
        participant_b_id=current_user.id,
        participant_a_role='parent'
    ).first()
    
    if not conv:
        # Find the student related to this parent and this prof
        # For simplicity, we just use the first student of this parent
        # But we can also leave etudiant_concerne_id empty or take it from the form
        etu_id = request.form.get('etudiant_id', type=int)
        
        conv = Conversation(
            type='parent_professeur',
            participant_a_id=parent.utilisateur_id,
            participant_a_role='parent',
            participant_b_id=current_user.id,
            etudiant_concerne_id=etu_id
        )
        db.session.add(conv)
        db.session.commit()
        
    return redirect(url_for('professeur.conversation', conv_id=conv.id))


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


# ── Les routes pour les posts et le sujet ont été déplacées vers l'Espace Études ──
# ── Messagerie Privée (Google Classroom Style) ──────────────────────
@prof_bp.route('/messages', defaults={'conv_id': None})
@prof_bp.route('/messages/<int:conv_id>')
@login_required
@professeur_requis
def messages(conv_id):
    prof = get_prof()
    
    # Fetch all conversations for this professor
    conversations = Conversation.query.filter_by(
        participant_b_id=prof.id
    ).order_by(Conversation.date_dernier_message.desc()).all()
    
    active_conv = None
    if conv_id:
        active_conv = Conversation.query.get_or_404(conv_id)
        if active_conv.participant_b_id != prof.id:
            abort(403)
        # Marquer les messages comme lus (optionnel mais recommandé)
        for msg in active_conv.messages:
            if msg.expediteur_id != current_user.id and not msg.est_lu:
                msg.est_lu = True
                msg.date_lecture = datetime.now(timezone.utc)
        db.session.commit()
    elif conversations:
        active_conv = conversations[0]
        
    return render_template('professeur/messages.html', 
                           conversations=conversations, 
                           active_conv=active_conv)

@prof_bp.route('/envoyer_message_conv/<int:conv_id>', methods=['POST'])
@login_required
@professeur_requis
def envoyer_message_conv(conv_id):
    prof = get_prof()
    conv = Conversation.query.get_or_404(conv_id)
    if conv.participant_b_id != prof.id:
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
        
        from app.services.notif_service import notifier_message
        notifier_message(db, current_user.id, conv.etudiant_concerne.utilisateur.id, conv.id, "Nouveau message du professeur")
        db.session.commit()
        
    return redirect(url_for('professeur.messages', conv_id=conv.id))
