# =============================================================
#  EduNova — sockets/chat.py
#  Événements SocketIO : chat temps réel + statut en ligne
# =============================================================
from datetime import datetime, timezone
from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
from app.extensions import socketio, db
from app.models.communication import (Message, Conversation,
                                       StatutConnexion, Notification)


@socketio.on('connect')
def on_connect():
    if current_user.is_authenticated:
        # Rejoindre la salle personnelle
        join_room(f'user_{current_user.id}')
        # Mettre à jour statut en ligne
        _set_online(current_user.id, request.sid, True)
        emit('connected', {'user_id': current_user.id})


@socketio.on('disconnect')
def on_disconnect():
    if current_user.is_authenticated:
        _set_online(current_user.id, None, False)


@socketio.on('join_conversation')
def on_join_conv(data):
    conv_id = data.get('conv_id')
    if conv_id:
        join_room(f'conv_{conv_id}')


@socketio.on('leave_conversation')
def on_leave_conv(data):
    conv_id = data.get('conv_id')
    if conv_id:
        leave_room(f'conv_{conv_id}')


@socketio.on('send_message')
def on_send_message(data):
    """
    data = {conv_id: int, contenu: str}
    Enregistre le message en BDD et le diffuse en temps réel.
    """
    if not current_user.is_authenticated:
        return

    conv_id = data.get('conv_id')
    contenu = (data.get('contenu') or '').strip()
    if not conv_id or not contenu:
        return

    conv = Conversation.query.get(conv_id)
    if not conv:
        return

    # Vérifier accès
    if (conv.participant_a_id != current_user.id
            and conv.participant_b_id != current_user.id):
        return

    # Déterminer le rôle
    role = current_user.role if current_user.role in ('etudiant','parent','professeur') else 'professeur'

    # Enregistrer
    msg = Message(
        conversation_id           = conv_id,
        expediteur_utilisateur_id = current_user.id,
        expediteur_role           = role,
        contenu                   = contenu,
    )
    db.session.add(msg)
    db.session.commit()

    payload = {
        'id'        : msg.id,
        'conv_id'   : conv_id,
        'contenu'   : contenu,
        'expediteur': current_user.id,
        'role'      : role,
        'date'      : msg.date_envoi.isoformat(),
    }

    # Émettre dans la salle de conversation
    emit('new_message', payload, room=f'conv_{conv_id}')

    # Notifier le destinataire dans sa salle personnelle
    dest_id = (conv.participant_b_id
               if current_user.id == conv.participant_a_id
               else conv.participant_a_id)
    dest_role = ('professeur'
                 if current_user.id == conv.participant_a_id
                 else conv.participant_a_role)

    emit('notification_message', {
        'conv_id': conv_id,
        'de'     : current_user.username if hasattr(current_user, 'username') else str(current_user.id),
        'extrait': contenu[:80],
    }, room=f'user_{dest_id}')

    # Créer la notification en BDD
    notif = Notification(
        type              = 'message_recu',
        destinataire_id   = dest_id,
        destinataire_role = dest_role,
        titre             = 'Nouveau message',
        contenu           = contenu[:120],
        reference_table   = 'conversations',
        reference_id      = conv_id,
    )
    db.session.add(notif)
    db.session.commit()


@socketio.on('typing')
def on_typing(data):
    conv_id = data.get('conv_id')
    if conv_id and current_user.is_authenticated:
        emit('user_typing', {'user_id': current_user.id},
             room=f'conv_{conv_id}', include_self=False)


@socketio.on('mark_read')
def on_mark_read(data):
    conv_id = data.get('conv_id')
    if conv_id and current_user.is_authenticated:
        Message.query.filter_by(conversation_id=conv_id, est_lu=False).filter(
            Message.expediteur_utilisateur_id != current_user.id
        ).update({'est_lu': True})
        db.session.commit()
        emit('messages_read', {'conv_id': conv_id, 'by': current_user.id},
             room=f'conv_{conv_id}')


# ── Helpers ───────────────────────────────────────────────────
def _set_online(user_id: int, socket_id, en_ligne: bool):
    try:
        sc = StatutConnexion.query.filter_by(utilisateur_id=user_id).first()
        if not sc:
            sc = StatutConnexion(utilisateur_id=user_id)
            db.session.add(sc)
        sc.est_en_ligne      = en_ligne
        sc.socket_id         = socket_id
        sc.derniere_activite = datetime.now(timezone.utc)
        db.session.commit()
    except Exception:
        db.session.rollback()
