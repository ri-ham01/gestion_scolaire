import os
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import render_template, redirect, url_for, request, flash, session, current_app, abort, send_from_directory
from flask_login import login_required, current_user, login_user

from app.blueprints.espace_etudes import espace_etudes_bp
from app.services.auth_service import authentifier
from app.extensions import db
from app.models.academic import AnneeScolaire, Semestre
from app.models.program import AffectationEnseignement, Inscription
from app.models.pedagogy import Cours, Devoir, SoumissionDevoir, PostProfesseur, CommentairePost
from app.models.communication import Conversation, Message

# Helper function for file uploads
def save_file(file_obj, subfolder=''):
    if not file_obj or file_obj.filename == '':
        return None, None
    filename = secure_filename(file_obj.filename)
    # Check allowed extensions
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'webp'})
    if ext not in allowed:
        return None, None

    # Determine type
    if ext == 'pdf': file_type = 'pdf'
    elif ext in ['doc', 'docx']: file_type = 'word'
    elif ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']: file_type = 'image'
    else: file_type = 'autre'

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_filename = f"{timestamp}_{filename}"
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, unique_filename)
    file_obj.save(file_path)
    
    # Return relative path for DB
    return f"{subfolder}/{unique_filename}", file_type


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
    affectations = AffectationEnseignement.query.filter_by(professeur_id=prof.id, est_active=True).all()
    
    selected_aff = None
    cours_list = []
    devoirs_list = []
    posts_list = []

    aff_id = request.args.get('aff_id', type=int)
    if aff_id:
        selected_aff = AffectationEnseignement.query.get(aff_id)
        if selected_aff and selected_aff.professeur_id == prof.id:
            cours_list = Cours.query.filter_by(affectation_id=selected_aff.id).order_by(Cours.date_publication.desc()).all()
            devoirs_list = Devoir.query.filter_by(affectation_id=selected_aff.id).order_by(Devoir.date_limite_soumission.desc()).all()
            posts_list = PostProfesseur.query.filter_by(affectation_id=selected_aff.id).order_by(PostProfesseur.created_at.desc()).all()
        else:
            selected_aff = None

    return render_template('espace_etudes/professeur.html', 
                           affectations=affectations,
                           selected_aff=selected_aff,
                           cours_list=cours_list,
                           devoirs_list=devoirs_list,
                           posts_list=posts_list)


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
        if selected_aff:
            cours_list = Cours.query.filter_by(affectation_id=selected_aff.id).order_by(Cours.date_publication.desc()).all()
            devoirs_list = Devoir.query.filter_by(affectation_id=selected_aff.id).order_by(Devoir.date_limite_soumission.desc()).all()
            posts_list = PostProfesseur.query.filter_by(affectation_id=selected_aff.id).order_by(PostProfesseur.created_at.desc()).all()

    return render_template('espace_etudes/etudiant.html',
                           cursus=cursus,
                           selected_aff=selected_aff,
                           cours_list=cours_list,
                           devoirs_list=devoirs_list,
                           posts_list=posts_list)


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

    file_path, file_type = save_file(fichier, 'cours')
    if not file_path:
        flash("Type de fichier non autorisé. Utilisez PDF, Word ou Image.", "danger")
        return redirect(url_for('espace_etudes.professeur_dashboard', aff_id=aff_id))

    cours = Cours(
        affectation_id=aff.id,
        titre=titre,
        type_contenu=file_type,
        fichier_url=file_path,
        nom_fichier_original=fichier.filename,
        est_publie=True,
        date_publication=datetime.now(timezone.utc),
        publie_par=current_user.professeur.id
    )
    db.session.add(cours)
    db.session.commit()
    flash("Cours publié avec succès.", "success")
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

    file_path, file_type = save_file(fichier, 'devoirs')

    devoir = Devoir(
        affectation_id=aff.id,
        titre=titre,
        description="Veuillez soumettre votre solution avant la date limite.",
        fichier_url=file_path,
        type_fichier=file_type,
        nom_fichier_original=fichier.filename if fichier else None,
        date_publication=datetime.now(timezone.utc),
        date_limite_soumission=date_limite,
        est_publie=True,
        publie_par=current_user.professeur.id
    )
    db.session.add(devoir)
    db.session.commit()
    flash("Devoir publié avec succès.", "success")
    return redirect(url_for('espace_etudes.professeur_dashboard', aff_id=aff_id))


@espace_etudes_bp.route('/post/publier', methods=['POST'])
@login_required
def publier_post():
    if current_user.role != 'professeur': return abort(403)
    aff_id = request.form.get('aff_id')
    contenu = request.form.get('contenu')
    
    aff = AffectationEnseignement.query.get_or_404(aff_id)
    post = PostProfesseur(
        professeur_id=current_user.professeur.id,
        affectation_id=aff.id,
        contenu=contenu
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
        return redirect(url_for('espace_etudes.professeur_dashboard', aff_id=post.affectation_id))
    else:
        return redirect(url_for('espace_etudes.etudiant_dashboard', aff_id=post.affectation_id))


# --- ACTIONS ETUDIANT ---

@espace_etudes_bp.route('/etudiant/devoir/soumettre', methods=['POST'])
@login_required
def soumettre_devoir():
    if current_user.role != 'etudiant': return abort(403)
    devoir_id = request.form.get('devoir_id')
    fichier = request.files.get('fichier')
    
    devoir = Devoir.query.get_or_404(devoir_id)
    
    file_path, file_type = save_file(fichier, 'soumissions')
    if not file_path:
        flash("Veuillez sélectionner un fichier valide (PDF, Word).", "danger")
        return redirect(url_for('espace_etudes.etudiant_dashboard', aff_id=devoir.affectation_id))

    soumission = SoumissionDevoir(
        devoir_id=devoir.id,
        etudiant_id=current_user.etudiant.id,
        fichier_url=file_path,
        type_fichier=file_type,
        nom_fichier_original=fichier.filename,
        statut='soumis',
        date_soumission=datetime.now(timezone.utc)
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
    if type == 'cours': obj = Cours.query.get_or_404(id)
    elif type == 'devoir': obj = Devoir.query.get_or_404(id)
    elif type == 'soumission': obj = SoumissionDevoir.query.get_or_404(id)
    else: abort(404)

    if not obj.fichier_url: abort(404)
    upload_dir = current_app.config['UPLOAD_FOLDER']
    full_path = os.path.join(upload_dir, obj.fichier_url)
    if not os.path.exists(full_path): abort(404)
    
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    return send_from_directory(directory, filename, as_attachment=True, download_name=obj.nom_fichier_original)


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
            
        return render_template('espace_etudes/chat_cours.html', cours=cours, conversation=conv)
        
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
            return render_template('espace_etudes/chat_cours.html', cours=cours, conversation=conv)
        else:
            conversations = Conversation.query.filter_by(
                type='cours_etudiant_professeur',
                cours_id=cours.id
            ).all()
            # Pour faire simple, on va passer la liste des conversations au template professeur
            # On peut réutiliser le dashboard ou faire une page simple
            return render_template('espace_etudes/chat_liste.html', cours=cours, conversations=conversations)

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
    db.session.commit()
    
    if current_user.role == 'etudiant':
        return redirect(url_for('espace_etudes.chat_cours', cours_id=cours.id))
    else:
        return redirect(url_for('espace_etudes.chat_cours', cours_id=cours.id, etudiant_id=conv.participant_a_id))


