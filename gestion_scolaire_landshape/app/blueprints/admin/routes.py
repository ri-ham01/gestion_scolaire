# =============================================================
#  EduNova — blueprints/admin/routes.py
#  Tableau de bord administration complète
# =============================================================
from datetime import datetime, timezone
from flask import (render_template, redirect, url_for, request,
                   flash)
from flask_login import login_required, current_user
from app.blueprints.admin import admin_bp
from app.extensions import db
from app.utils.decorators import admin_requis
from app.utils.helpers import sauvegarder_fichier
from app.models.user import Utilisateur
from app.models.profiles import (Professeur, Etudiant, Parent,
                                   ParentEtudiant)
from app.models.academic import AnneeScolaire, Semestre, Niveau, Specialite, Section
from app.models.program  import Matiere, Inscription, AffectationEnseignement
from app.models.communication import Annonce, AnnonceFichier
from app.models.presence import Presence
from app.models.planning import PdfEmploiTemps
from app.models.audit import JournalAdmin


def _upsert_affectation(professeur_id: int, matiere_id: int,
                        section_id: int, semestre_id: int) -> None:
    """Crée ou met à jour une affectation (contrainte unique matière/section/semestre)."""
    aff = AffectationEnseignement.query.filter_by(
        matiere_id=matiere_id, section_id=section_id, semestre_id=semestre_id
    ).first()
    if aff:
        aff.professeur_id = professeur_id
        aff.est_active = True
        aff.date_affectation = datetime.now(timezone.utc).date()
    else:
        db.session.add(AffectationEnseignement(
            professeur_id=professeur_id,
            matiere_id=matiere_id,
            section_id=section_id,
            semestre_id=semestre_id,
            date_affectation=datetime.now(timezone.utc).date(),
            est_active=True,
        ))


# ─────────────────────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────────────────────
@admin_bp.route('/dashboard')
@login_required
@admin_requis
def dashboard():
    stats = {
        'etudiants'   : Etudiant.query.filter_by(est_actif=True).count(),
        'professeurs' : Professeur.query.filter_by(est_actif=True).count(),
        'specialites' : Specialite.query.filter_by(est_active=True).count(),
        'annonces'    : Annonce.query.filter_by(est_publie=True).count(),
    }
    annee = AnneeScolaire.get_active()
    return render_template('admin/dashboard.html', stats=stats, annee=annee)


# ─────────────────────────────────────────────────────────────
#  PROFESSEURS
# ─────────────────────────────────────────────────────────────
@admin_bp.route('/professeurs')
@login_required
@admin_requis
def professeurs():
    q   = request.args.get('q', '').strip()
    query = Professeur.query
    if q:
        query = query.filter(
            (Professeur.nom.ilike(f'%{q}%'))
            | (Professeur.prenom.ilike(f'%{q}%'))
            | (Utilisateur.username.ilike(f'%{q}%'))
        ).join(Utilisateur, Professeur.utilisateur_id == Utilisateur.id)
    profs = query.order_by(Professeur.nom).all()
    specialites = Specialite.query.filter_by(est_active=True).all()
    annee = AnneeScolaire.get_active()
    sections = Section.query.filter_by(annee_scolaire_id=annee.id if annee else 0).all()
    matieres = Matiere.query.filter_by(est_active=True).all()
    semestre = Semestre.query.filter_by(est_actif=True).first()
    from app.models.program import Programme
    programmes = Programme.query.all()
    semestres = Semestre.query.filter_by(annee_scolaire_id=annee.id).order_by(Semestre.numero).all() if annee else []
    return render_template('admin/professeurs.html', profs=profs, q=q,
                           specialites=specialites, sections=sections, matieres=matieres,
                           semestre=semestre, semestres=semestres, programmes=programmes, annee=annee)


@admin_bp.route('/professeurs/ajouter', methods=['POST'])
@login_required
@admin_requis
def ajouter_professeur():
    from app.services.auth_service import creer_compte_professeur
    try:
        nom            = request.form['nom'].strip()
        prenom         = request.form['prenom'].strip()
        spe_id         = request.form.get('specialite_id', type=int)
        spe_code       = request.form.get('specialite_code', '').strip()
        if spe_id:
            spe = Specialite.query.get(spe_id)
            if not spe:
                raise ValueError('Spécialité invalide.')
            spe_code = spe.code
        elif spe_code:
            spe = Specialite.query.filter_by(code=spe_code.upper()).first()
            spe_id = spe.id if spe else None
        else:
            raise ValueError('Veuillez sélectionner une spécialité.')

        date_naissance = request.form.get('date_naissance') or None
        lieu_naissance = request.form.get('lieu_naissance') or None
        grade          = request.form.get('grade') or None

        if date_naissance:
            date_naissance = datetime.strptime(date_naissance, '%Y-%m-%d').date()

        section_id = request.form.get('section_id', type=int)
        matiere_ids = [int(m) for m in request.form.getlist('matiere_ids') if m]
        semestre_id = request.form.get('semestre_id', type=int)

        if not section_id:
            raise ValueError('Veuillez sélectionner une section.')
        if not matiere_ids:
            raise ValueError('Veuillez cocher au moins une matière enseignée.')
        if not semestre_id:
            sem = Semestre.query.filter_by(est_actif=True).first()
            if not sem:
                raise ValueError('Aucun semestre actif. Activez un semestre avant d\'ajouter un professeur.')
            semestre_id = sem.id

        sec = Section.query.get(section_id)
        if sec and sec.specialite_id != spe_id:
            raise ValueError('La section choisie ne correspond pas à la spécialité sélectionnée.')

        user, password = creer_compte_professeur(
            nom=nom, prenom=prenom, specialite_code=spe_code,
            date_naissance=date_naissance, lieu_naissance=lieu_naissance,
            grade=grade, specialite_id=spe_id,
        )

        for matiere_id in matiere_ids:
            _upsert_affectation(
                professeur_id=user.professeur.id,
                matiere_id=matiere_id,
                section_id=section_id,
                semestre_id=semestre_id,
            )
        db.session.commit()

        _log_action('CREATE_PROFESSEUR', 'professeurs', user.id)
        flash(f'Professeur {prenom} {nom} créé — Username: {user.username} | Mot de passe: {password}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.professeurs'))


@admin_bp.route('/professeurs/supprimer/<int:prof_id>', methods=['POST'])
@login_required
@admin_requis
def supprimer_professeur(prof_id):
    from app.services.professeur_service import supprimer_professeur_definitif
    Professeur.query.get_or_404(prof_id)
    try:
        supprimer_professeur_definitif(prof_id)
        db.session.commit()
        _log_action('DELETE_PROFESSEUR', 'professeurs', prof_id)
        flash('Professeur supprimé définitivement de la base de données.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la suppression : {str(e)}', 'danger')
    return redirect(url_for('admin.professeurs'))


@admin_bp.route('/professeurs/modifier/<int:prof_id>', methods=['GET', 'POST'])
@login_required
@admin_requis
def modifier_professeur(prof_id):
    prof = Professeur.query.get_or_404(prof_id)
    if request.method == 'POST':
        try:
            prof.nom    = request.form['nom'].strip().upper()
            prof.prenom = request.form['prenom'].strip().capitalize()
            prof.grade  = request.form.get('grade') or None
            dn          = request.form.get('date_naissance')
            if dn:
                prof.date_naissance = datetime.strptime(dn, '%Y-%m-%d').date()
            prof.lieu_naissance = request.form.get('lieu_naissance') or None
            db.session.commit()
            _log_action('UPDATE_PROFESSEUR', 'professeurs', prof_id)
            flash('Professeur mis à jour.', 'success')
            return redirect(url_for('admin.professeurs'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')
    return render_template('admin/modifier_professeur.html', prof=prof)


# ─────────────────────────────────────────────────────────────
#  ÉTUDIANTS
# ─────────────────────────────────────────────────────────────
@admin_bp.route('/etudiants')
@login_required
@admin_requis
def etudiants():
    q     = request.args.get('q', '').strip()
    query = Etudiant.query
    if q:
        query = query.join(Utilisateur, Etudiant.utilisateur_id == Utilisateur.id).filter(
            (Etudiant.nom.ilike(f'%{q}%'))
            | (Etudiant.prenom.ilike(f'%{q}%'))
            | (Utilisateur.username.ilike(f'%{q}%'))
        )
    etus        = query.order_by(Etudiant.nom).all()
    specialites = Specialite.query.filter_by(est_active=True).all()
    niveaux     = Niveau.query.filter_by(est_actif=True).order_by(Niveau.ordre).all()
    annee       = AnneeScolaire.get_active()
    sections    = Section.query.filter_by(annee_scolaire_id=annee.id if annee else 0).all()
    return render_template('admin/etudiants.html', etus=etus, q=q,
                           specialites=specialites, niveaux=niveaux, sections=sections, annee=annee)


@admin_bp.route('/etudiants/ajouter', methods=['POST'])
@login_required
@admin_requis
def ajouter_etudiant():
    from app.services.auth_service import creer_compte_etudiant
    try:
        nom            = request.form['nom'].strip()
        prenom         = request.form['prenom'].strip()
        section_id     = int(request.form['section_id'])
        section        = Section.query.get_or_404(section_id)
        date_naissance = request.form.get('date_naissance') or None
        lieu_naissance = request.form.get('lieu_naissance') or None
        sexe           = request.form.get('sexe') or None

        if date_naissance:
            date_naissance = datetime.strptime(date_naissance, '%Y-%m-%d').date()

        annee = AnneeScolaire.get_active()
        if not annee:
            raise Exception('Aucune année scolaire active.')

        # Extract group suffix from section code
        code_sec = section.code_section.upper()
        suffix = 'A'
        if code_sec.endswith('B') or code_sec.endswith('2'):
            suffix = 'B'
        elif code_sec.endswith('C') or code_sec.endswith('3'):
            suffix = 'C'
        elif code_sec.endswith('D') or code_sec.endswith('4'):
            suffix = 'D'
            
        user, password = creer_compte_etudiant(
            nom=nom, prenom=prenom,
            specialite_code=section.specialite.code,
            niveau_ordre=section.niveau.ordre,
            annee_debut=annee.annee_debut,
            date_naissance=date_naissance,
            lieu_naissance=lieu_naissance,
            sexe=sexe,
            groupe_suffix=suffix
        )
        # Créer l'inscription
        insc = Inscription(
            etudiant_id       = user.etudiant.id,
            section_id        = section_id,
            annee_scolaire_id = annee.id,
            date_inscription  = datetime.now(timezone.utc).date(),
        )
        db.session.add(insc)
        
        # Créer le compte parent associé automatiquement
        from app.models.profiles import Parent, ParentEtudiant
        from app.models import Utilisateur
        from werkzeug.security import generate_password_hash
        import string, random

        prenom_clean = prenom.lower().replace(' ', '').replace('é', 'e').replace('è', 'e').replace('â', 'a')
        nom_clean = nom.lower().replace(' ', '').replace('é', 'e').replace('è', 'e').replace('â', 'a')
        email = f"parent.{prenom_clean}.{nom_clean}@edu.nova.dz"
        
        parent_user = Utilisateur(
            username=email,
            email=email,
            password_hash=generate_password_hash('12345'),
            role='parent'
        )
        db.session.add(parent_user)
        db.session.flush()
        
        parent_profile = Parent(
            utilisateur_id=parent_user.id,
            nom=nom,
            prenom='Parent de ' + prenom,
            email=email,
            telephone='0' + ''.join(random.choices(string.digits, k=9))
        )
        db.session.add(parent_profile)
        db.session.flush()
        
        pe = ParentEtudiant(parent_id=parent_profile.id, etudiant_id=user.etudiant.id, lien='Père')
        db.session.add(pe)
        
        db.session.commit()

        _log_action('CREATE_ETUDIANT', 'etudiants', user.id)
        flash(f'Étudiant {prenom} {nom} créé — Username: {user.username} | Mot de passe: {password}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.etudiants'))


@admin_bp.route('/etudiants/supprimer/<int:etu_id>', methods=['POST'])
@login_required
@admin_requis
def supprimer_etudiant(etu_id):
    etu = Etudiant.query.get_or_404(etu_id)
    try:
        etu.est_actif              = False
        etu.utilisateur.est_actif  = False
        db.session.commit()
        _log_action('DELETE_ETUDIANT', 'etudiants', etu_id)
        flash('Étudiant désactivé.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.etudiants'))


@admin_bp.route('/etudiants/modifier/<int:etu_id>', methods=['GET', 'POST'])
@login_required
@admin_requis
def modifier_etudiant(etu_id):
    etu = Etudiant.query.get_or_404(etu_id)
    if request.method == 'POST':
        try:
            etu.nom    = request.form['nom'].strip().upper()
            etu.prenom = request.form['prenom'].strip().capitalize()
            dn          = request.form.get('date_naissance')
            if dn:
                etu.date_naissance = datetime.strptime(dn, '%Y-%m-%d').date()
            etu.lieu_naissance = request.form.get('lieu_naissance') or None
            db.session.commit()
            _log_action('UPDATE_ETUDIANT', 'etudiants', etu_id)
            flash('Étudiant mis à jour.', 'success')
            return redirect(url_for('admin.etudiants'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')
    return render_template('admin/modifier_etudiant.html', etu=etu)


# ─────────────────────────────────────────────────────────────
#  PARENTS
# ─────────────────────────────────────────────────────────────
@admin_bp.route('/parents')
@login_required
@admin_requis
def parents():
    parents_list = Parent.query.order_by(Parent.nom).all()
    etudiants_list = Etudiant.query.filter_by(est_actif=True).all()
    return render_template('admin/parents.html', parents=parents_list, etudiants=etudiants_list)


@admin_bp.route('/parents/ajouter', methods=['POST'])
@login_required
@admin_requis
def ajouter_parent():
    from app.services.auth_service import creer_compte_parent
    try:
        nom           = request.form['nom'].strip()
        prenom        = request.form['prenom'].strip()
        email         = request.form['email'].strip().lower()
        telephone     = request.form.get('telephone') or None
        profession    = request.form.get('profession') or None
        statut_emploi = request.form.get('statut_emploi') or None
        etudiant_id   = request.form.get('etudiant_id', type=int)
        lien          = request.form.get('lien', 'tuteur')

        user, password = creer_compte_parent(
            nom=nom, prenom=prenom, email=email,
            telephone=telephone, profession=profession, statut_emploi=statut_emploi
        )
        # Lier au(x) étudiant(s)
        if etudiant_id:
            pe = ParentEtudiant(
                parent_id=user.parent.id,
                etudiant_id=etudiant_id,
                lien=lien,
            )
            db.session.add(pe)
            db.session.commit()

        _log_action('CREATE_PARENT', 'parents', user.id)
        flash(f'Parent {prenom} {nom} créé — Email: {email} | Mot de passe: {password}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.parents'))


# ─────────────────────────────────────────────────────────────
#  SPÉCIALITÉS & MATIÈRES
# ─────────────────────────────────────────────────────────────
@admin_bp.route('/specialites')
@login_required
@admin_requis
def specialites():
    q    = request.args.get('q', '').strip()
    spes = Specialite.query
    if q:
        spes = spes.filter(
            (Specialite.nom.ilike(f'%{q}%')) | (Specialite.code.ilike(f'%{q}%'))
        )
    spes    = spes.order_by(Specialite.nom).all()
    niveaux = Niveau.query.filter_by(est_actif=True).order_by(Niveau.ordre).all()
    return render_template('admin/specialites_matieres.html', spes=spes, q=q, niveaux=niveaux)


@admin_bp.route('/specialites/ajouter', methods=['POST'])
@login_required
@admin_requis
def ajouter_specialite():
    try:
        code = request.form['code'].strip().upper()
        nom  = request.form['nom'].strip()
        spe  = Specialite(code=code, nom=nom,
                           nom_ar=request.form.get('nom_ar') or None,
                           nom_en=request.form.get('nom_en') or None)
        db.session.add(spe)
        db.session.commit()
        flash(f'Spécialité {code} ajoutée.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.specialites'))


@admin_bp.route('/specialites/supprimer/<int:spe_id>', methods=['POST'])
@login_required
@admin_requis
def supprimer_specialite(spe_id):
    spe = Specialite.query.get_or_404(spe_id)
    try:
        spe.est_active = False
        db.session.commit()
        flash('Spécialité désactivée.', 'success')
    except Exception as e:
        db.session.rollback()
    return redirect(url_for('admin.specialites'))


@admin_bp.route('/specialites/<int:spe_id>/matieres', methods=['GET', 'POST'])
@login_required
@admin_requis
def specialite_matieres(spe_id):
    from app.models.program import Programme, Matiere
    spe = Specialite.query.get_or_404(spe_id)
    niveaux = Niveau.query.filter_by(est_actif=True).order_by(Niveau.ordre).all()
    all_matieres = Matiere.query.filter_by(est_active=True).all()
    semestre = Semestre.query.filter_by(est_actif=True).first()
    
    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'add':
                niveau_id = int(request.form.get('niveau_id'))
                coef = int(request.form.get('coefficient', 1))
                sem_num = int(request.form.get('semestre_numero', semestre.numero if semestre else 1))
                mode = request.form.get('matiere_mode', 'existing')

                if mode == 'new':
                    code_m = request.form.get('nouveau_code', '').strip().upper()
                    nom_m = request.form.get('nouveau_nom', '').strip()
                    if not code_m or not nom_m:
                        raise ValueError('Code et nom de la nouvelle matière sont obligatoires.')
                    matiere = Matiere.query.filter_by(code=code_m).first()
                    if not matiere:
                        matiere = Matiere(code=code_m, nom=nom_m,
                                          nom_ar=request.form.get('nouveau_nom_ar') or None,
                                          nom_en=request.form.get('nouveau_nom_en') or None)
                        db.session.add(matiere)
                        db.session.flush()
                    matiere_id = matiere.id
                else:
                    matiere_id = int(request.form.get('matiere_id'))

                exists = Programme.query.filter_by(
                    matiere_id=matiere_id, specialite_id=spe.id,
                    niveau_id=niveau_id, semestre_numero=sem_num
                ).first()
                if exists:
                    flash('Cette matière est déjà liée à cette spécialité pour ce niveau et semestre.', 'warning')
                else:
                    prog = Programme(
                        matiere_id=matiere_id, specialite_id=spe.id,
                        niveau_id=niveau_id, semestre_numero=sem_num, coefficient=coef
                    )
                    db.session.add(prog)
                    db.session.commit()
                    flash('Matière ajoutée à la spécialité.', 'success')
            elif action == 'delete':
                prog_id = int(request.form.get('prog_id'))
                prog = Programme.query.get_or_404(prog_id)
                db.session.delete(prog)
                db.session.commit()
                flash('Matière retirée de la spécialité.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur : {str(e)}', 'danger')
            
        return redirect(url_for('admin.specialite_matieres', spe_id=spe.id))
        
    programmes = Programme.query.filter_by(specialite_id=spe.id).all()
    annee_active = AnneeScolaire.get_active()
    semestres = (Semestre.query.filter_by(annee_scolaire_id=annee_active.id)
                 .order_by(Semestre.numero).all()) if annee_active else []
    return render_template('admin/specialite_matieres_detail.html',
                           spe=spe, programmes=programmes, niveaux=niveaux,
                           all_matieres=all_matieres, semestres=semestres, semestre=semestre)


@admin_bp.route('/matieres/ajouter', methods=['POST'])
@login_required
@admin_requis
def ajouter_matiere():
    try:
        code = request.form['code'].strip().upper()
        nom  = request.form['nom'].strip()
        mat  = Matiere(code=code, nom=nom)
        db.session.add(mat)
        db.session.commit()
        flash(f'Matière {code} ajoutée.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.specialites'))


# ─────────────────────────────────────────────────────────────
#  AFFECTATIONS ENSEIGNEMENT
# ─────────────────────────────────────────────────────────────
@admin_bp.route('/affectations')
@login_required
@admin_requis
def affectations():
    annee    = AnneeScolaire.get_active()
    semestre = Semestre.query.filter_by(est_actif=True).first()
    if semestre:
        aff_list = (AffectationEnseignement.query
                    .filter_by(est_active=True, semestre_id=semestre.id)
                    .order_by(AffectationEnseignement.date_affectation.desc())
                    .all())
    else:
        aff_list = []
    profs    = Professeur.query.filter_by(est_actif=True).all()
    sections = Section.query.filter_by(annee_scolaire_id=annee.id if annee else 0).all()
    matieres = Matiere.query.filter_by(est_active=True).all()
    return render_template('admin/affectations.html',
                           affectations=aff_list, profs=profs,
                           sections=sections, matieres=matieres, semestre=semestre)


@admin_bp.route('/affectations/ajouter', methods=['POST'])
@login_required
@admin_requis
def ajouter_affectation():
    try:
        _upsert_affectation(
            professeur_id=int(request.form['professeur_id']),
            matiere_id=int(request.form['matiere_id']),
            section_id=int(request.form['section_id']),
            semestre_id=int(request.form['semestre_id']),
        )
        db.session.commit()
        flash('Affectation enregistrée.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.affectations'))


# ─────────────────────────────────────────────────────────────
#  ANNONCES
# ─────────────────────────────────────────────────────────────
@admin_bp.route('/annonces')
@login_required
@admin_requis
def annonces():
    anns = (Annonce.query
            .order_by(Annonce.est_epinglee.desc(), Annonce.created_at.desc())
            .all())
    return render_template('admin/annonces.html', annonces=anns)


@admin_bp.route('/annonces/ajouter', methods=['POST'])
@login_required
@admin_requis
def ajouter_annonce():
    try:
        ann = Annonce(
            admin_id         = current_user.administrateur.id,
            titre            = request.form['titre'].strip(),
            contenu          = request.form['contenu'].strip(),
            public_cible     = request.form.get('public_cible', 'tous'),
            est_publie       = bool(request.form.get('est_publie')),
            est_epinglee     = bool(request.form.get('est_epinglee')),
            date_publication = datetime.now(timezone.utc),
        )
        db.session.add(ann)
        db.session.flush()
        # Pièces jointes
        if 'fichiers' in request.files:
            for f in request.files.getlist('fichiers'):
                if f.filename:
                    chemin = sauvegarder_fichier(f, 'annonces')
                    if chemin:
                        af = AnnonceFichier(annonce_id=ann.id, fichier_url=chemin,
                                            nom_fichier=f.filename)
                        db.session.add(af)
        db.session.commit()
        flash('Annonce publiée.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.annonces'))


@admin_bp.route('/annonces/supprimer/<int:ann_id>', methods=['POST'])
@login_required
@admin_requis
def supprimer_annonce(ann_id):
    ann = Annonce.query.get_or_404(ann_id)
    db.session.delete(ann)
    db.session.commit()
    flash('Annonce supprimée.', 'success')
    return redirect(url_for('admin.annonces'))


# ─────────────────────────────────────────────────────────────
#  EMPLOIS DU TEMPS (upload PDF)
# ─────────────────────────────────────────────────────────────
@admin_bp.route('/emploi-du-temps')
@login_required
@admin_requis
def emploi_du_temps():
    semestres   = Semestre.query.all()
    specialites = Specialite.query.filter_by(est_active=True).all()
    pdfs        = PdfEmploiTemps.query.order_by(PdfEmploiTemps.updated_at.desc()).all()
    return render_template('admin/emploi_temps.html',
                           semestres=semestres, specialites=specialites, pdfs=pdfs)


@admin_bp.route('/emploi-du-temps/uploader', methods=['POST'])
@login_required
@admin_requis
def uploader_edt():
    try:
        spe_id     = int(request.form['specialite_id'])
        sem_id     = int(request.form['semestre_id'])
        type_pdf   = request.form['type_pdf']   # hebdomadaire | examens
        fichier    = request.files.get('fichier')

        if not fichier or fichier.filename == '':
            raise Exception('Aucun fichier sélectionné.')

        from app.utils.helpers import allowed_file
        if not allowed_file(fichier.filename, 'document'):
            raise Exception('Seuls les fichiers PDF sont acceptés pour l\'emploi du temps.')

        chemin = sauvegarder_fichier(fichier, 'emplois_temps', f'{type_pdf}_{spe_id}')
        if not chemin:
            raise Exception('Échec de l\'upload.')

        # Upsert
        record = PdfEmploiTemps.query.filter_by(
            specialite_id=spe_id, semestre_id=sem_id, type_pdf=type_pdf
        ).first()
        if not record:
            record = PdfEmploiTemps(
                specialite_id=spe_id, semestre_id=sem_id, type_pdf=type_pdf,
                genere_par=current_user.administrateur.id
            )
            db.session.add(record)

        record.fichier_url  = chemin
        record.nom_fichier  = fichier.filename
        record.updated_at   = datetime.now(timezone.utc)
        db.session.commit()
        flash('PDF d\'emploi du temps mis à jour.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.emploi_du_temps'))


# ─────────────────────────────────────────────────────────────
#  JUSTIFICATIONS D'ABSENCES
# ─────────────────────────────────────────────────────────────
@admin_bp.route('/justifications')
@login_required
@admin_requis
def justifications():
    en_attente = (Presence.query
                  .filter_by(statut='absent', statut_justification='en_attente')
                  .order_by(Presence.date_enregistrement.desc())
                  .all())
    return render_template('admin/justifications.html', presences=en_attente)


@admin_bp.route('/justifications/accepter/<int:pres_id>', methods=['POST'])
@login_required
@admin_requis
def accepter_justification(pres_id):
    pres = Presence.query.get_or_404(pres_id)
    try:
        pres.accepter_justification(current_user.administrateur.id)
        db.session.commit()
        flash('Justification acceptée — absence annulée.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.justifications'))


@admin_bp.route('/justifications/refuser/<int:pres_id>', methods=['POST'])
@login_required
@admin_requis
def refuser_justification(pres_id):
    pres = Presence.query.get_or_404(pres_id)
    try:
        pres.refuser_justification(current_user.administrateur.id)
        db.session.commit()
        flash('Justification refusée.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.justifications'))


# ─────────────────────────────────────────────────────────────
#  ANNÉES SCOLAIRES & SEMESTRES
# ─────────────────────────────────────────────────────────────
@admin_bp.route('/annees-scolaires')
@login_required
@admin_requis
def annees_scolaires():
    annees = AnneeScolaire.query.order_by(AnneeScolaire.annee_debut.desc()).all()
    return render_template('admin/annees_scolaires.html', annees=annees)


@admin_bp.route('/annees-scolaires/ajouter', methods=['POST'])
@login_required
@admin_requis
def ajouter_annee():
    try:
        debut = int(request.form['annee_debut'])
        label = f'{debut}-{debut+1}'
        an    = AnneeScolaire(label=label, annee_debut=debut, annee_fin=debut+1)
        db.session.add(an)
        db.session.flush() # Pour avoir an.id
        
        # Add basic semestres
        import datetime
        d1_start = datetime.date(debut, 9, 1)
        d1_end   = datetime.date(debut + 1, 1, 31)
        d2_start = datetime.date(debut + 1, 2, 1)
        d2_end   = datetime.date(debut + 1, 6, 30)

        s1 = Semestre(annee_scolaire_id=an.id, numero=1, date_debut=d1_start, date_fin=d1_end, est_actif=True)
        s2 = Semestre(annee_scolaire_id=an.id, numero=2, date_debut=d2_start, date_fin=d2_end, est_actif=False)
        db.session.add(s1)
        db.session.add(s2)
        
        db.session.commit()
        flash(f'Année {label} et ses 2 semestres ont été créés.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.annees_scolaires'))


@admin_bp.route('/annees-scolaires/activer/<int:an_id>', methods=['POST'])
@login_required
@admin_requis
def activer_annee(an_id):
    try:
        AnneeScolaire.query.update({'est_active': False})
        an = AnneeScolaire.query.get_or_404(an_id)
        an.est_active = True
        db.session.commit()
        flash('Année scolaire activée.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur : {str(e)}', 'danger')
    return redirect(url_for('admin.annees_scolaires'))


# ─────────────────────────────────────────────────────────────
#  HELPER INTERNE
# ─────────────────────────────────────────────────────────────
def _log_action(action: str, table: str, record_id: int = None):
    try:
        from flask import request as req
        log = JournalAdmin(
            admin_id=current_user.administrateur.id,
            action=action,
            table_affectee=table,
            enregistrement_id=record_id,
            adresse_ip=req.remote_addr,
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass
