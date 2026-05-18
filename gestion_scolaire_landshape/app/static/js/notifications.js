/**
 * EduNova — Notifications JS
 * Real-time notifications via SocketIO + polling fallback
 */

(function () {
    const badge   = document.getElementById('notifBadge');
    const panel   = document.getElementById('notifPanel');
    const list    = document.getElementById('notifList');
    const toggle  = document.getElementById('notifToggle');
    const markAll = document.getElementById('markAllRead');

    let unreadCount = 0;

    // ── Toggle Panel ──────────────────────────────────────────
    if (toggle) {
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            panel.classList.toggle('active');
            if (panel.classList.contains('active')) {
                loadNotifications();
            }
        });
        document.addEventListener('click', (e) => {
            if (!panel.contains(e.target) && e.target !== toggle) {
                panel.classList.remove('active');
            }
        });
    }

    // ── Mark All Read ─────────────────────────────────────────
    if (markAll) {
        markAll.addEventListener('click', () => {
            fetch('/api/notifications/marquer-lues', { method: 'POST',
                headers: { 'Content-Type': 'application/json',
                           'X-CSRFToken': getCsrf() }
            }).then(() => {
                unreadCount = 0;
                updateBadge();
                loadNotifications();
            });
        });
    }

    // ── Load Notifications ────────────────────────────────────
    function loadNotifications() {
        fetch('/api/notifications')
            .then(r => r.json())
            .then(data => {
                unreadCount = data.non_lues || 0;
                updateBadge();
                renderNotifications(data.notifications || []);
            })
            .catch(() => {});
    }

    function renderNotifications(notifs) {
        if (!list) return;
        if (notifs.length === 0) {
            list.innerHTML = '<li class="notif-empty"><i class="fa-regular fa-bell-slash"></i> Aucune notification</li>';
            return;
        }
        list.innerHTML = notifs.map(n => `
            <li class="notif-item ${n.est_lu ? '' : 'unread'}" data-id="${n.id}">
                <div class="notif-icon notif-${n.type}">
                    <i class="fa-solid ${getNotifIcon(n.type)}"></i>
                </div>
                <div class="notif-body">
                    <p class="notif-title">${escapeHtml(n.titre)}</p>
                    <p class="notif-text">${escapeHtml(n.contenu)}</p>
                    <span class="notif-time">${timeAgo(n.date_envoi)}</span>
                </div>
            </li>
        `).join('');
    }

    function updateBadge() {
        if (!badge) return;
        if (unreadCount > 0) {
            badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
            badge.style.display = 'flex';
            badge.classList.add('pulse');
            setTimeout(() => badge.classList.remove('pulse'), 600);
        } else {
            badge.style.display = 'none';
        }
    }

    function getNotifIcon(type) {
        const icons = {
            'absence_enregistree'   : 'fa-calendar-xmark',
            'absence_justifiee'     : 'fa-calendar-check',
            'absence_refusee'       : 'fa-ban',
            'note_publiee'          : 'fa-star',
            'message_recu'          : 'fa-envelope',
            'annonce'               : 'fa-bullhorn',
            'devoir_publie'         : 'fa-file-pen',
            'cours_publie'          : 'fa-book-open',
            'correction_publiee'    : 'fa-file-circle-check',
            'releve_disponible'     : 'fa-file-contract',
            'exclusion_absences'    : 'fa-triangle-exclamation',
            'seuil_absences_atteint': 'fa-exclamation',
        };
        return icons[type] || 'fa-bell';
    }

    function timeAgo(dateStr) {
        if (!dateStr) return '';
        const diff = Date.now() - new Date(dateStr).getTime();
        const minutes = Math.floor(diff / 60000);
        if (minutes < 1)  return 'À l\'instant';
        if (minutes < 60) return `Il y a ${minutes} min`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24)   return `Il y a ${hours}h`;
        const days = Math.floor(hours / 24);
        return `Il y a ${days}j`;
    }

    function escapeHtml(str) {
        const d = document.createElement('div');
        d.appendChild(document.createTextNode(str || ''));
        return d.innerHTML;
    }

    function getCsrf() {
        const m = document.cookie.match(/csrf_token=([^;]+)/);
        return m ? m[1] : '';
    }

    // ── SocketIO Real-time ────────────────────────────────────
    if (typeof io !== 'undefined') {
        const socket = io({ transports: ['websocket', 'polling'] });

        socket.on('connect', () => {
            socket.emit('join_room', { user_id: window.EDUNOVA_USER_ID || null });
        });

        socket.on('nouvelle_notification', (data) => {
            unreadCount++;
            updateBadge();
            showToast(data.titre, data.contenu, data.type);
        });

        socket.on('nouveau_message', (data) => {
            unreadCount++;
            updateBadge();
            showToast('Nouveau message', data.contenu || 'Vous avez un nouveau message.', 'message_recu');
        });
    }

    // ── Toast Notifications ───────────────────────────────────
    function showToast(titre, contenu, type) {
        const container = getToastContainer();
        const toast = document.createElement('div');
        toast.className = `toast-notif toast-${type || 'info'}`;
        toast.innerHTML = `
            <div class="toast-icon"><i class="fa-solid ${getNotifIcon(type)}"></i></div>
            <div class="toast-content">
                <strong>${escapeHtml(titre)}</strong>
                <p>${escapeHtml(contenu)}</p>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        container.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('show'));
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    function getToastContainer() {
        let c = document.getElementById('toastContainer');
        if (!c) {
            c = document.createElement('div');
            c.id = 'toastContainer';
            c.className = 'toast-container';
            document.body.appendChild(c);
        }
        return c;
    }

    // ── Initial Load + Poll every 60s ─────────────────────────
    loadNotifications();
    setInterval(loadNotifications, 60000);

})();
