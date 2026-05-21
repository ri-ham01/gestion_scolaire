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
    return render_template('parent/dashboard.html',
                           parent=parent, enfants=enfants, notifs_count=notifs_count)


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
    for etu in enfants:
        releves_par_enfant[etu.id] = ReleverNotes.query.filter_by(
            etudiant_id=etu.id).all()
    return render_template('parent/releve.html',
                           parent=parent, enfants=enfants,
                           releves=releves_par_enfant)


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
        if insc and sem:
            affs = AffectationEnseignement.query.filter_by(
                section_id=insc.section_id,
                semestre_id=sem.id,
                est_active=True
            ).all()
            profs_par_enfant[etu.id] = [
                {'prof': a.professeur, 'matiere': a.matiere, 'aff_id': a.id}
                for a in affs
            ]
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
