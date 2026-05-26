import os
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import render_template, redirect, url_for, request, flash, session, current_app, abort, send_file
from flask_login import login_required, current_user, login_user

from app.blueprints.espace_etudes import espace_etudes_bp
from app.services.auth_service import authentifier
from app.extensions import db
from app.models.academic import AnneeScolaire, Semestre
from app.models.program import AffectationEnseignement, Inscription
from app.models.pedagogy import Cours, Devoir, SoumissionDevoir, PostProfesseur, CommentairePost
from app.models.communication import Conversation, Message

from app.utils.helpers import (sauvegarder_fichier, allowed_file,
                               type_fichier_pedagogique, type_contenu_cours,
                               chemin_absolu_upload)
from app.models.evaluation import CorrectionExamen
from app.models.profiles import Etudiant
from app.services.notif_service import (notifier_cours_publie, notifier_devoir_publie,
                                        notifier_message_cours)


def _etudiant_peut_acceder_affectation(etu, aff) -> bool:
    """Vérifie qu'un étudiant est inscrit dans la section de l'affectation."""
    return Inscription.query.filter_by(
        etudiant_id=etu.id, section_id=aff.section_id, statut='actif'
    ).first() is not None


def _messages_non_lus_count(user_id: int) -> int:
    from app.models.communication import Message
    convs = Conversation.query.filter(
        (Conversation.participant_a_id == user_id) |
        (Conversation.participant_b_id == user_id)
    ).filter_by(type='cours_etudiant_professeur', est_active=True).all()
    total = 0
    for c in convs:
        total += c.messages.filter(
            Message.expediteur_utilisateur_id != user_id,
            Message.est_lu == False  # noqa: E712
        ).count()
    return total


def _prof_affectations(prof_id: int, semestre_id: int | None = None):
    q = AffectationEnseignement.query.filter_by(
        professeur_id=prof_id, est_active=True)
    if semestre_id:
        q = q.filter_by(semestre_id=semestre_id)
    return q.order_by(AffectationEnseignement.id).all()


@espace_etudes_bp.route('/', methods=['GET'])
def index():
    if current_user.is_authenticated:
        if current_user.role == 'etudiant':
            return redirect(url_for('espace_etudes.etudiant_dashboard'))
        elif current_user.role == 'professeur':
            return redirect(url_for('espace_etudes.professeur_dashboard'))
    return redirect(url_for('espace_etudes.login'))


@espace_etudes_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('espace_etudes.index'))

    error = None
    if request.method == 'POST':
        role_choisi = request.form.get('role')
        identifiant = request.form.get('identifiant', '').strip()
        password    = request.form.get('password', '')

        if role_choisi not in ['etudiant', 'professeur']:
            error = "Veuillez sélectionner votre rôle."
        else:
            user, msg = authentifier(identifiant, password)
            if user:
                if user.role != role_choisi:
                    error = f"Ce compte n'est pas un compte {role_choisi}."
                else:
                    login_user(user, remember=False)
                    session['lang'] = user.preference_langue
                    return redirect(url_for('espace_etudes.index'))
            else:
                error = msg

    return render_template('espace_etudes/login.html', error=error)


@espace_etudes_bp.route('/professeur', methods=['GET'])
@login_required
def professeur_dashboard():
    if current_user.role != 'professeur':
        return redirect(url_for('espace_etudes.login'))

    prof = current_user.professeur
    semestre_id = request.args.get('semestre_id', type=int)
    if not semestre_id:
        sem_actif = Semestre.query.filter_by(est_actif=True).first()
        semestre_id = sem_actif.id if sem_actif else None

    annee = AnneeScolaire.get_active()
    semestres = (Semestre.query.filter_by(annee_scolaire_id=annee.id)
                 .order_by(Semestre.numero).all()) if annee else []
    affectations = _prof_affectations(prof.id, semestre_id)

    selected_aff = None
    cours_list = []
    devoirs_list = []
    posts_list = []
    tab = request.args.get('tab', 'cours')

    aff_id = request.args.get('aff_id', type=int)
    if aff_id:
        selected_aff = AffectationEnseignement.query.get(aff_id)
        if selected_aff and selected_aff.professeur_id == prof.id:
            cours_list = (Cours.query.filter_by(affectation_id=selected_aff.id)
                          .order_by(Cours.date_publication.desc()).all())
            devoirs_list = (Devoir.query.filter_by(affectation_id=selected_aff.id)
                            .order_by(Devoir.date_limite_soumission.desc()).all())
            from sqlalchemy import or_
            prof_id = selected_aff.professeur_id
            posts_list = (PostProfesseur.query.filter(
                or_(
                    PostProfesseur.affectation_id == selected_aff.id,
                    db.and_(PostProfesseur.type_public == 'tous',
                            PostProfesseur.professeur_id == prof_id),
                )
            ).order_by(PostProfesseur.created_at.desc()).all())
        else:
            selected_aff = None

    return render_template('espace_etudes/professeur.html',
                           affectations=affectations,
                           selected_aff=selected_aff,
                           cours_list=cours_list,
                           devoirs_list=devoirs_list,
                           posts_list=posts_list,
                           semestres=semestres,
                           semestre_id=semestre_id,
                           tab=tab,
                           messages_non_lus=_messages_non_lus_count(current_user.id))


@espace_etudes_bp.route('/etudiant', methods=['GET'])
@login_required
def etudiant_dashboard():
    if current_user.role != 'etudiant':
        return redirect(url_for('espace_etudes.login'))

    etu = current_user.etudiant
    # Récupérer toutes les inscriptions de l'étudiant pour construire son "Cursus"
    inscriptions = Inscription.query.filter_by(etudiant_id=etu.id).order_by(Inscription.annee_scolaire_id.desc()).all()
    
    # Structure: cursus[annee][semestre] = list(affectations)
    cursus = {}
    for ins in inscriptions:
        annee = ins.annee_scolaire
        if annee not in cursus:
            cursus[annee] = {}
        
        # On affiche les affectations des semestres actifs
        # Par défaut on montre semestre 1 et 2 pour les années passées
        # Pour l'année en cours on montre jusqu'au semestre courant
        semestres_a_montrer = [1, 2] if ins.statut != 'actif' else [1, ins.semestre_courant]
        semestres_a_montrer = list(set(semestres_a_montrer)) # unique
        
        for sem_num in semestres_a_montrer:
            sem_obj = Semestre.query.filter_by(annee_scolaire_id=annee.id, numero=sem_num).first()
            if sem_obj:
                affs = AffectationEnseignement.query.filter_by(section_id=ins.section_id, semestre_id=sem_obj.id, est_active=True).all()
                if affs:
                    cursus[annee][sem_obj] = affs

    selected_aff = None
    cours_list = []
    devoirs_list = []
    posts_list = []

    aff_id = request.args.get('aff_id', type=int)
    if aff_id:
        selected_aff = AffectationEnseignement.query.get(aff_id)
        if selected_aff and _etudiant_peut_acceder_affectation(etu, selected_aff):
            cours_list = Cours.query.filter_by(
                affectation_id=selected_aff.id, est_publie=True
            ).order_by(Cours.date_publication.desc()).all()
            devoirs_list = Devoir.query.filter_by(
                affectation_id=selected_aff.id, est_publie=True
            ).order_by(Devoir.date_limite_soumission.desc()).all()
            from sqlalchemy import or_
            prof_id = selected_aff.professeur_id
            posts_list = (PostProfesseur.query.filter(
                or_(
                    PostProfesseur.affectation_id == selected_aff.id,
                    db.and_(PostProfesseur.type_public == 'tous',
                            PostProfesseur.professeur_id == prof_id),
                )
            ).order_by(PostProfesseur.created_at.desc()).all())
        else:
            selected_aff = None

    annee_sel = request.args.get('annee_id', type=int)
    sem_sel = request.args.get('semestre_id', type=int)
    if not annee_sel and inscriptions:
        annee_sel = inscriptions[0].annee_scolaire_id
    if not sem_sel and annee_sel:
        ins = next((i for i in inscriptions if i.annee_scolaire_id == annee_sel), inscriptions[0] if inscriptions else None)
        if ins:
            sem = Semestre.query.filter_by(annee_scolaire_id=annee_sel, numero=ins.semestre_courant).first()
            sem_sel = sem.id if sem else None

    afficher_affs = []
    semestres_disponibles = []
    if annee_sel:
        for annee, sem_map in cursus.items():
            if annee.id == annee_sel:
                semestres_disponibles = list(sem_map.keys())
                break
        if not sem_sel and semestres_disponibles:
            sem_sel = semestres_disponibles[-1].id
        ins = next((i for i in inscriptions if i.annee_scolaire_id == annee_sel), None)
        if ins and sem_sel:
            afficher_affs = AffectationEnseignement.query.filter_by(
                section_id=ins.section_id, semestre_id=sem_sel, est_active=True
            ).all()

    return render_template('espace_etudes/etudiant.html',
                           cursus=cursus,
                           selected_aff=selected_aff,
                           cours_list=cours_list,
                           devoirs_list=devoirs_list,
                           posts_list=posts_list,
                           inscriptions=inscriptions,
                           afficher_affs=afficher_affs,
                           semestres_disponibles=semestres_disponibles,
                           annee_sel=annee_sel,
                           sem_sel=sem_sel,
                           tab=request.args.get('tab', 'cours'),
                           messages_non_lus=_messages_non_lus_count(current_user.id))


# --- ACTIONS PROFESSEUR ---

@espace_etudes_bp.route('/professeur/cours/publier', methods=['POST'])
@login_required
def publier_cours():
    if current_user.role != 'professeur': return abort(403)
    aff_id = request.form.get('aff_id')
    titre = request.form.get('titre')
    fichier = request.files.get('fichier')
    
    aff = AffectationEnseignement.query.get_or_404(aff_id)
    if aff.professeur_id != current_user.professeur.id: return abort(403)

    if not fichier or not allowed_file(fichier.filename, 'all'):
        flash("Type de fichier non autorisé. Utilisez PDF, Word ou Image.", "danger")
        return redirect(url_for('espace_etudes.professeur_dashboard', aff_id=aff_id))

    file_path = sauvegarder_fichier(fichier, 'cours')
    if not file_path:
        flash("Échec de l'enregistrement du fichier.", "danger")
        return redirect(url_for('espace_etudes.professeur_dashboard', aff_id=aff_id))

    ordre = Cours.query.filter_by(affectation_id=aff.id).count() + 1
    cours = Cours(
        affectation_id=aff.id,
        titre=titre,
        type_contenu=type_contenu_cours(fichier.filename),
        fichier_url=file_path,
        nom_fichier_original=fichier.filename,
        ordre=ordre,
        est_publie=True,
        date_publication=datetime.now(timezone.utc),
        publie_par=current_user.professeur.id
    )
    db.session.add(cours)
    db.session.flush()
    notifier_cours_publie(aff.id, aff.matiere.nom, cours.id)
    db.session.commit()
    flash("Cours publié et accessible à tous les étudiants de cette classe.", "success")
    return redirect(url_for('espace_etudes.professeur_dashboard', aff_id=aff_id))


@espace_etudes_bp.route('/professeur/devoirs/publier', methods=['POST'])
@login_required
def publier_devoir():
    if current_user.role != 'professeur': return abort(403)
    aff_id = request.form.get('aff_id')
    titre = request.form.get('titre')
    date_limite_str = request.form.get('date_limite')
    fichier = request.files.get('fichier')

    aff = AffectationEnseignement.query.get_or_404(aff_id)
    if aff.professeur_id != current_user.professeur.id: return abort(403)

    try:
        # datetime-local is format YYYY-MM-DDTHH:MM
        date_limite = datetime.strptime(date_limite_str, '%Y-%m-%dT%H:%M')
    except:
        date_limite = datetime.now()

    file_path = None
    file_type = None
    if fichier and fichier.filename:
        if not allowed_file(fichier.filename, 'all'):
            flash("Type de fichier non autorisé pour le sujet du devoir.", "danger")
            return redirect(url_for('espace_etudes.professeur_dashboard', aff_id=aff_id))
        file_path = sauvegarder_fichier(fichier, 'devoirs')
        if not file_path:
            flash("Échec de l'enregistrement du fichier du devoir.", "danger")
            return redirect(url_for('espace_etudes.professeur_dashboard', aff_id=aff_id))
        file_type = type_fichier_pedagogique(fichier.filename)

    devoir = Devoir(
        affectation_id=aff.id,
        titre=titre,
        description="Veuillez soumettre votre solution avant la date limite.",
        fichier_url=file_path,
        type_fichier=file_type,
        nom_fichier_original=fichier.filename if fichier and fichier.filename else None,
        date_publication=datetime.now(timezone.utc),
        date_limite_soumission=date_limite,
        est_publie=True,
        publie_par=current_user.professeur.id
    )
    db.session.add(devoir)
    db.session.flush()
    notifier_devoir_publie(aff.id, aff.matiere.nom, devoir.id)
    db.session.commit()
    flash("Devoir publié et accessible à tous les étudiants de cette classe.", "success")
    return redirect(url_for('espace_etudes.professeur_dashboard', aff_id=aff_id))


@espace_etudes_bp.route('/post/publier', methods=['POST'])
@login_required
def publier_post():
    if current_user.role != 'professeur': return abort(403)
    aff_id = request.form.get('aff_id')
    contenu = request.form.get('contenu')
    
    aff = AffectationEnseignement.query.get_or_404(aff_id)
    if aff.professeur_id != current_user.professeur.id:
        abort(403)
    type_public = request.form.get('type_public', 'section')
    post = PostProfesseur(
        professeur_id=current_user.professeur.id,
        affectation_id=aff.id if type_public == 'section' else None,
        contenu=contenu,
        type_public=type_public,
    )
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('espace_etudes.professeur_dashboard', aff_id=aff_id))


@espace_etudes_bp.route('/post/commenter', methods=['POST'])
@login_required
def commenter_post():
    post_id = request.form.get('post_id')
    contenu = request.form.get('contenu')
    
    post = PostProfesseur.query.get_or_404(post_id)
    comment = CommentairePost(
        post_id=post.id,
        auteur_id=current_user.id,
        auteur_role=current_user.role,
        contenu=contenu
    )
    db.session.add(comment)
    db.session.commit()
    
    if current_user.role == 'professeur':
        aff_id = post.affectation_id or request.args.get('aff_id')
        return redirect(url_for('espace_etudes.professeur_dashboard', aff_id=aff_id, tab='posts'))
    aff_id = post.affectation_id or request.form.get('aff_id')
    return redirect(url_for('espace_etudes.etudiant_dashboard', aff_id=aff_id, tab='posts'))


# --- ACTIONS ETUDIANT ---

@espace_etudes_bp.route('/etudiant/devoir/soumettre', methods=['POST'])
@login_required
def soumettre_devoir():
    if current_user.role != 'etudiant': return abort(403)
    devoir_id = request.form.get('devoir_id')
    fichier = request.files.get('fichier')
    
    devoir = Devoir.query.get_or_404(devoir_id)
    
    if not fichier or not allowed_file(fichier.filename, 'all'):
        flash("Veuillez sélectionner un fichier valide (PDF, Word).", "danger")
        return redirect(url_for('espace_etudes.etudiant_dashboard', aff_id=devoir.affectation_id))

    file_path = sauvegarder_fichier(fichier, 'soumissions')
    if not file_path:
        flash("Échec de l'enregistrement du fichier.", "danger")
        return redirect(url_for('espace_etudes.etudiant_dashboard', aff_id=devoir.affectation_id))
    file_type = type_fichier_pedagogique(fichier.filename)

    existing = SoumissionDevoir.query.filter_by(
        devoir_id=devoir.id, etudiant_id=current_user.etudiant.id
    ).first()
    if existing:
        existing.fichier_url = file_path
        existing.type_fichier = file_type
        existing.nom_fichier_original = fichier.filename
        existing.date_soumission = datetime.now(timezone.utc)
    else:
        soumission = SoumissionDevoir(
            devoir_id=devoir.id,
            etudiant_id=current_user.etudiant.id,
            fichier_url=file_path,
            type_fichier=file_type,
            nom_fichier_original=fichier.filename,
            date_soumission=datetime.now(timezone.utc),
        )
        db.session.add(soumission)
    db.session.commit()
    flash("Devoir soumis avec succès.", "success")
    return redirect(url_for('espace_etudes.etudiant_dashboard', aff_id=devoir.affectation_id))


# --- FICHIERS ---
@espace_etudes_bp.route('/fichier/<type>/<int:id>')
@login_required
def telecharger_fichier(type, id):
    obj = None
    aff = None
    if type == 'cours':
        obj = Cours.query.get_or_404(id)
        aff = obj.affectation
    elif type == 'devoir':
        obj = Devoir.query.get_or_404(id)
        aff = obj.affectation
    elif type == 'soumission':
        obj = SoumissionDevoir.query.get_or_404(id)
        aff = obj.devoir.affectation
    else:
        abort(404)

    if not obj.fichier_url:
        abort(404)

    if current_user.role == 'professeur':
        if aff.professeur_id != current_user.professeur.id:
            abort(403)
    elif current_user.role == 'etudiant':
        etu = current_user.etudiant
        if type == 'soumission':
            if obj.etudiant_id != etu.id:
                abort(403)
        elif not _etudiant_peut_acceder_affectation(etu, aff):
            abort(403)
    else:
        abort(403)

    chemin = chemin_absolu_upload(obj.fichier_url)
    if not chemin or not os.path.exists(chemin):
        abort(404)

    download_name = obj.nom_fichier_original or os.path.basename(chemin)
    return send_file(chemin, as_attachment=True, download_name=download_name)


# --- MESSAGES (Espace Études) ---
@espace_etudes_bp.route('/messages')
@login_required
def messages_list():
    if current_user.role == 'professeur':
        prof_uid = current_user.id
        convs = Conversation.query.filter_by(
            type='cours_etudiant_professeur',
            participant_b_id=prof_uid,
            est_active=True,
        ).order_by(Conversation.date_dernier_message.desc()).all()
    elif current_user.role == 'etudiant':
        convs = Conversation.query.filter_by(
            type='cours_etudiant_professeur',
            participant_a_id=current_user.id,
            est_active=True,
        ).order_by(Conversation.date_dernier_message.desc()).all()
    else:
        return redirect(url_for('espace_etudes.login'))

    return render_template('espace_etudes/messages.html',
                           conversations=convs,
                           messages_non_lus=_messages_non_lus_count(current_user.id))


@espace_etudes_bp.route('/messages/<int:conv_id>')
@login_required
def messages_thread(conv_id):
    conv = Conversation.query.get_or_404(conv_id)
    if current_user.id not in (conv.participant_a_id, conv.participant_b_id):
        abort(403)

    for msg in conv.messages:
        if msg.expediteur_utilisateur_id != current_user.id and not msg.est_lu:
            msg.est_lu = True
            msg.date_lecture = datetime.now(timezone.utc)
    db.session.commit()

    cours = conv.cours
    etu = conv.etudiant_concerne
    msgs = conv.messages.order_by(Message.date_envoi).all()

    return render_template('espace_etudes/message_thread.html',
                           conversation=conv, cours=cours, etudiant=etu, msgs=msgs,
                           messages_non_lus=_messages_non_lus_count(current_user.id))


@espace_etudes_bp.route('/messages/envoyer', methods=['POST'])
@login_required
def messages_envoyer():
    conv_id = int(request.form['conversation_id'])
    contenu = request.form.get('contenu', '').strip()
    if not contenu:
        flash('Message vide.', 'warning')
        return redirect(request.referrer or url_for('espace_etudes.messages_list'))

    conv = Conversation.query.get_or_404(conv_id)
    if current_user.id not in (conv.participant_a_id, conv.participant_b_id):
        abort(403)

    msg = Message(
        conversation_id=conv.id,
        expediteur_utilisateur_id=current_user.id,
        expediteur_role=current_user.role,
        contenu=contenu,
    )
    db.session.add(msg)
    conv.date_dernier_message = datetime.now(timezone.utc)
    db.session.flush()

    cours_titre = conv.cours.titre if conv.cours else 'Cours'
    if current_user.role == 'etudiant':
        notifier_message_cours(conv.id, conv.participant_b_id, 'professeur', cours_titre)
    else:
        notifier_message_cours(conv.id, conv.participant_a_id, 'etudiant', cours_titre)

    db.session.commit()
    return redirect(url_for('espace_etudes.messages_thread', conv_id=conv.id))


# --- CHAT PAR COURS ---
@espace_etudes_bp.route('/chat/cours/<int:cours_id>')
@login_required
def chat_cours(cours_id):
    cours = Cours.query.get_or_404(cours_id)
    
    if current_user.role == 'etudiant':
        # Trouver ou créer la conversation
        conv = Conversation.query.filter_by(
            type='cours_etudiant_professeur',
            participant_a_id=current_user.id,
            cours_id=cours.id
        ).first()
        
        if not conv:
            conv = Conversation(
                type='cours_etudiant_professeur',
                participant_a_id=current_user.id,
                participant_a_role='etudiant',
                participant_b_id=cours.affectation.professeur.utilisateur_id,
                sujet=f"Question sur le cours: {cours.titre}",
                matiere_id=cours.affectation.matiere_id,
                etudiant_concerne_id=current_user.etudiant.id,
                cours_id=cours.id
            )
            db.session.add(conv)
            db.session.commit()

        return redirect(url_for('espace_etudes.messages_thread', conv_id=conv.id))
        
    elif current_user.role == 'professeur':
        # Pour le prof, on affiche la liste des étudiants ayant posé une question sur ce cours
        # S'il y a un paramètre etudiant_id, on affiche la conv, sinon on liste
        etu_id = request.args.get('etudiant_id', type=int)
        if etu_id:
            conv = Conversation.query.filter_by(
                type='cours_etudiant_professeur',
                participant_a_id=etu_id,
                cours_id=cours.id
            ).first()
            if not conv:
                abort(404)
            return redirect(url_for('espace_etudes.messages_thread', conv_id=conv.id))
        return redirect(url_for('espace_etudes.messages_list'))

@espace_etudes_bp.route('/chat/envoyer', methods=['POST'])
@login_required
def envoyer_message_cours():
    cours_id = request.form.get('cours_id')
    contenu = request.form.get('contenu')
    
    cours = Cours.query.get_or_404(cours_id)
    
    if current_user.role == 'etudiant':
        conv = Conversation.query.filter_by(type='cours_etudiant_professeur', participant_a_id=current_user.id, cours_id=cours.id).first()
    else:
        etudiant_id = request.form.get('etudiant_id')
        conv = Conversation.query.filter_by(type='cours_etudiant_professeur', participant_a_id=etudiant_id, cours_id=cours.id).first()
        
    if not conv:
        abort(404)
        
    msg = Message(
        conversation_id=conv.id,
        expediteur_utilisateur_id=current_user.id,
        expediteur_role=current_user.role,
        contenu=contenu
    )
    db.session.add(msg)
    conv.date_dernier_message = datetime.now(timezone.utc)
    db.session.flush()
    cours_titre = cours.titre
    if current_user.role == 'etudiant':
        notifier_message_cours(conv.id, conv.participant_b_id, 'professeur', cours_titre)
    else:
        notifier_message_cours(conv.id, conv.participant_a_id, 'etudiant', cours_titre)
    db.session.commit()

    if current_user.role == 'etudiant':
        return redirect(url_for('espace_etudes.messages_thread', conv_id=conv.id))
    return redirect(url_for('espace_etudes.messages_thread', conv_id=conv.id))


