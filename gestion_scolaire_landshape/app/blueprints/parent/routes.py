# =============================================================
#  EduNova — blueprints/parent/routes.py
# =============================================================
import os
from datetime import datetime, timezone
from flask import (render_template, redirect, url_for, request,
                   flash, send_file, abort, jsonify, current_app)
from flask_login import login_required, current_user
from app.blueprints.parent import parent_bp
from app.extensions import db
from app.utils.decorators import parent_requis
from app.utils.helpers import sauvegarder_fichier
from app.models.profiles import Parent
from app.models.presence import Presence, CompteurAbsences
from app.models.program import AffectationEnseignement
from app.models.evaluation import ReleverNotes
from app.models.communication import Conversation, Message, Notification
from app.services.notif_service import notifier_message


def get_parent() -> Parent:
    return current_user.parent


@parent_bp.route('/dashboard')
@login_required
@parent_requis
def dashboard():
    parent = get_parent()
    enfants = parent.get_enfants()
    notifs_count = Notification.query.filter_by(
        destinataire_id=current_user.id, est_lu=False).count()
        
    # Messages non lus
    unread_messages_count = Message.query.join(Conversation).filter(
        Conversation.participant_a_id == current_user.id,
        Message.expediteur_utilisateur_id != current_user.id,
        Message.est_lu == False
    ).count()

    return render_template('parent/dashboard.html',
                           parent=parent, enfants=enfants, 
                           notifs_count=notifs_count,
                           unread_messages_count=unread_messages_count)


# ── Absences ──────────────────────────────────────────────────
@parent_bp.route('/absences')
@login_required
@parent_requis
def absences():
    parent  = get_parent()
    enfants = parent.get_enfants()
    # Récupérer toutes les absences des enfants du parent
    absences_data = []
    for etu in enfants:
        presences = (Presence.query
                     .filter_by(etudiant_id=etu.id, statut='absent')
                     .order_by(Presence.date_enregistrement.desc())
                     .all())
        insc = etu.get_inscription_active()
        compteur = None
        if insc:
            sem = __import__('app.models.academic', fromlist=['Semestre']).Semestre
            sem_actif = sem.query.filter_by(est_actif=True).first()
            if sem_actif:
                compteur = CompteurAbsences.query.filter_by(
                    etudiant_id=etu.id,
                    inscription_id=insc.id,
                    semestre_id=sem_actif.id
                ).first()
        absences_data.append({
            'etudiant' : etu,
            'presences': presences,
            'compteur' : compteur,
        })
    return render_template('parent/absences.html',
                           parent=parent, absences_data=absences_data)


@parent_bp.route('/absences/justifier/<int:pres_id>', methods=['POST'])
@login_required
@parent_requis
def justifier_absence(pres_id):
    parent = get_parent()
    pres   = Presence.query.get_or_404(pres_id)

    # Vérifier que c'est bien un enfant du parent
    enfants_ids = [e.id for e in parent.get_enfants()]
    if pres.etudiant_id not in enfants_ids:
        abort(403)

    # Vérifier déjà justifié
    if pres.statut_justification is not None:
        flash('Cette absence a déjà été traitée.', 'warning')
        return redirect(url_for('parent.absences'))

    try:
        justification = request.form.get('justification', '').strip()
        fichier       = request.files.get('fichier')
        chemin        = None
        if fichier and fichier.filename:
            chemin = sauvegarder_fichier(fichier, 'justifications')

        pres.justification          = justification
        pres.fichier_justification  = chemin
        pres.justifie_par_parent_id = parent.id
        pres.date_justification     = datetime.now(timezone.utc)
        pres.statut_justification   = 'en_attente'
        db.session.commit()

        # Notifier l'administration
        from app.models.user import Utilisateur
        admins = Utilisateur.query.filter_by(role='admin', est_actif=True).all()
        from app.services.notif_service import envoyer_notification
        for admin in admins:
            envoyer_notification(
                destinataire_id=admin.id,
                destinataire_role='admin',
                type_notif='absence_justifiee',
                titre='Justification d\'absence reçue',
                contenu=f'{parent.nom_complet} a justifié l\'absence de '
                        f'{pres.etudiant.nom_complet}.',
                ref_table='presences',
                ref_id=pres_id,
            )
        flash('Justification envoyée. En attente de validation.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('parent.absences'))


# ── Relevé de notes ───────────────────────────────────────────
@parent_bp.route('/releve')
@login_required
@parent_requis
def releve():
    parent  = get_parent()
    enfants = parent.get_enfants()
    releves_par_enfant = {}
    notes_par_enfant = {}
    from app.models.evaluation import Note
    for etu in enfants:
        releves_par_enfant[etu.id] = ReleverNotes.query.filter_by(
            etudiant_id=etu.id).all()
        # Fetch real-time notes
        notes_par_enfant[etu.id] = Note.query.filter_by(etudiant_id=etu.id).all()
    return render_template('parent/releve.html',
                           parent=parent, enfants=enfants,
                           releves=releves_par_enfant,
                           notes_par_enfant=notes_par_enfant)


@parent_bp.route('/releve/telecharger/<string:token>')
@login_required
@parent_requis
def telecharger_releve(token):
    parent = get_parent()
    releve = ReleverNotes.query.filter_by(qr_code_token=token).first_or_404()
    # Vérifier appartenance
    enfants_ids = [e.id for e in parent.get_enfants()]
    if releve.etudiant_id not in enfants_ids:
        abort(403)
    chemin = os.path.join(current_app.config['UPLOAD_FOLDER'],
                          *releve.fichier_url.split('/')[1:])
    if not os.path.exists(chemin):
        abort(404)
    return send_file(chemin, as_attachment=True,
                     download_name=releve.nom_fichier or 'releve.pdf',
                     mimetype='application/pdf')


# ── Chat avec professeurs ─────────────────────────────────────
@parent_bp.route('/chat')
@login_required
@parent_requis
def chat():
    parent  = get_parent()
    enfants = parent.get_enfants()
    # Lister les professeurs des enfants (semestre actif)
    profs_par_enfant = {}
    from app.models.academic import Semestre
    sem = Semestre.query.filter_by(est_actif=True).first()
    for etu in enfants:
        insc = etu.get_inscription_active()
        if insc:
            affs = AffectationEnseignement.query.filter_by(
                section_id=insc.section_id
            ).all()
            profs_uniques = {}
            for a in affs:
                if a.professeur_id not in profs_uniques:
                    profs_uniques[a.professeur_id] = {'prof': a.professeur, 'matiere': a.matiere, 'aff_id': a.id}
            profs_par_enfant[etu.id] = list(profs_uniques.values())
    convs = Conversation.query.filter_by(
        participant_a_id=current_user.id,
        participant_a_role='parent'
    ).all()
    return render_template('parent/chat.html',
                           parent=parent, enfants=enfants,
                           profs_par_enfant=profs_par_enfant, convs=convs)


@parent_bp.route('/chat/nouvelle/<int:prof_user_id>/<int:etu_id>')
@login_required
@parent_requis
def nouvelle_conversation(prof_user_id, etu_id):
    conv = Conversation.query.filter_by(
        participant_a_id=current_user.id,
        participant_b_id=prof_user_id,
        participant_a_role='parent',
        etudiant_concerne_id=etu_id,
    ).first()
    if not conv:
        conv = Conversation(
            type='parent_professeur',
            participant_a_id=current_user.id,
            participant_a_role='parent',
            participant_b_id=prof_user_id,
            etudiant_concerne_id=etu_id,
        )
        db.session.add(conv)
        db.session.commit()
    return redirect(url_for('parent.conversation_detail', conv_id=conv.id))


@parent_bp.route('/chat/<int:conv_id>')
@login_required
@parent_requis
def conversation_detail(conv_id):
    conv = Conversation.query.get_or_404(conv_id)
    if conv.participant_a_id != current_user.id:
        abort(403)
    msgs = conv.messages.filter_by(supprime_par_expediteur=False).all()
    return render_template('parent/conversation.html', conv=conv, msgs=msgs)


@parent_bp.route('/chat/envoyer', methods=['POST'])
@login_required
@parent_requis
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
            expediteur_role='parent',
            contenu=contenu,
        )
        db.session.add(msg)
        db.session.commit()
        notifier_message(conv_id, current_user.id,
                         conv.participant_b_id, 'professeur')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# ── Modification Profil Parent & Enfant ───────────────────────
@parent_bp.route('/modifier', methods=['GET', 'POST'])
@login_required
@parent_requis
def modifier_profil():
    parent = get_parent()
    if request.method == 'POST':
        try:
            parent.nom        = request.form.get('nom', '').strip().upper()
            parent.prenom     = request.form.get('prenom', '').strip().capitalize()
            parent.profession = request.form.get('profession', '').strip()
            parent.adresse    = request.form.get('adresse', '').strip()
            parent.telephone  = request.form.get('telephone', '').strip()
            db.session.commit()
            flash('Vos informations ont été mises à jour avec succès.', 'success')
            return redirect(url_for('parent.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')
            
    return render_template('parent/modifier.html', parent=parent)


@parent_bp.route('/modifier-enfant/<int:etu_id>', methods=['GET', 'POST'])
@login_required
@parent_requis
def modifier_enfant(etu_id):
    parent = get_parent()
    enfants = parent.get_enfants()
    enfant = next((e for e in enfants if e.id == etu_id), None)
    if not enfant:
        abort(403)
        
    if request.method == 'POST':
        try:
            enfant.nom            = request.form.get('nom', '').strip().upper()
            enfant.prenom         = request.form.get('prenom', '').strip().capitalize()
            dn = request.form.get('date_naissance')
            if dn:
                enfant.date_naissance = datetime.strptime(dn, '%Y-%m-%d').date()
            enfant.lieu_naissance = request.form.get('lieu_naissance', '').strip()
            db.session.commit()
            flash(f'Les informations de {enfant.prenom} ont été mises à jour.', 'success')
            return redirect(url_for('parent.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')
            
    return render_template('parent/modifier.html', parent=parent, enfant=enfant)
