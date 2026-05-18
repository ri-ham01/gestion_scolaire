# =============================================================
#  EduNova — blueprints/api/routes.py
#  API JSON interne (notifications, messages, statut)
# =============================================================
from flask import jsonify, request
from flask_login import login_required, current_user
from app.blueprints.api import api_bp
from app.extensions import db
from app.models.communication import Notification, Message, Conversation, StatutConnexion


@api_bp.route('/notifications')
@login_required
def get_notifications():
    notifs = (Notification.query
              .filter_by(destinataire_id=current_user.id)
              .order_by(Notification.date_envoi.desc())
              .limit(20).all())
    return jsonify([{
        'id'     : n.id,
        'type'   : n.type,
        'titre'  : n.titre,
        'contenu': n.contenu,
        'est_lu' : n.est_lu,
        'date'   : n.date_envoi.isoformat(),
    } for n in notifs])


@api_bp.route('/notifications/marquer-lu/<int:notif_id>', methods=['POST'])
@login_required
def marquer_lu(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.destinataire_id != current_user.id:
        return jsonify({'error': 'Forbidden'}), 403
    notif.marquer_lu()
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/notifications/marquer-tout-lu', methods=['POST'])
@login_required
def marquer_tout_lu():
    Notification.query.filter_by(
        destinataire_id=current_user.id, est_lu=False
    ).update({'est_lu': True})
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/notifications/count')
@login_required
def count_notifications():
    count = Notification.query.filter_by(
        destinataire_id=current_user.id, est_lu=False).count()
    return jsonify({'count': count})


@api_bp.route('/messages/<int:conv_id>')
@login_required
def get_messages(conv_id):
    conv = Conversation.query.get_or_404(conv_id)
    # Vérifier accès
    if (conv.participant_a_id != current_user.id
            and conv.participant_b_id != current_user.id):
        return jsonify({'error': 'Forbidden'}), 403
    msgs = conv.messages.order_by(Message.date_envoi).all()
    return jsonify([{
        'id'        : m.id,
        'contenu'   : m.contenu,
        'expediteur': m.expediteur_utilisateur_id,
        'role'      : m.expediteur_role,
        'est_lu'    : m.est_lu,
        'date'      : m.date_envoi.isoformat(),
    } for m in msgs])


@api_bp.route('/messages/supprimer/<int:msg_id>', methods=['DELETE'])
@login_required
def supprimer_message(msg_id):
    msg  = Message.query.get_or_404(msg_id)
    side = request.json.get('side', 'moi')  # 'moi' | 'tous'
    if msg.expediteur_utilisateur_id == current_user.id:
        if side == 'tous':
            msg.supprime_par_expediteur   = True
            msg.supprime_par_destinataire = True
        else:
            msg.supprime_par_expediteur = True
    else:
        msg.supprime_par_destinataire = True
    db.session.commit()
    return jsonify({'ok': True})


@api_bp.route('/statut/ping', methods=['POST'])
@login_required
def ping_statut():
    """Appelé régulièrement par le JS pour maintenir le statut en ligne."""
    from datetime import datetime, timezone
    sc = StatutConnexion.query.filter_by(utilisateur_id=current_user.id).first()
    if not sc:
        sc = StatutConnexion(utilisateur_id=current_user.id)
        db.session.add(sc)
    sc.est_en_ligne       = True
    sc.derniere_activite  = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'ok': True})
