/**
 * EduNova — Chat JS
 * Real-time messaging via SocketIO with auto-scroll
 */

(function () {
    const chatBox   = document.getElementById('chatMessages');
    const chatForm  = document.getElementById('chatForm');
    const msgInput  = document.getElementById('msgInput');
    const convId    = window.EDUNOVA_CONV_ID || null;
    const myUserId  = window.EDUNOVA_MY_USER_ID || null;

    if (!chatBox || !convId) return;

    // Auto-scroll to bottom
    function scrollToBottom() {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
    scrollToBottom();

    // ── SocketIO Real-time ──────────────────────────────────
    let socket = null;
    if (typeof io !== 'undefined') {
        socket = io({ transports: ['websocket', 'polling'] });
        socket.on('connect', () => {
            socket.emit('rejoindre_conversation', { conv_id: convId });
        });

        socket.on('nouveau_message_chat', (data) => {
            if (parseInt(data.conv_id) === parseInt(convId)) {
                appendMessage(data);
                scrollToBottom();
            }
        });
    }

    // ── Send Message ────────────────────────────────────────
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const contenu = msgInput.value.trim();
            if (!contenu) return;

            const formData = new FormData();
            formData.append('conv_id', convId);
            formData.append('contenu', contenu);

            fetch(chatForm.action, {
                method: 'POST',
                body: formData,
            }).then(r => r.json()).then(data => {
                if (data.ok) {
                    msgInput.value = '';
                    // Message will appear via socket, but add immediately for UX
                    appendMessage({
                        expediteur_id: myUserId,
                        contenu: contenu,
                        date_envoi: new Date().toISOString(),
                        is_mine: true,
                    });
                    scrollToBottom();
                }
            }).catch(() => {});
        });
    }

    // ── Append Message ──────────────────────────────────────
    function appendMessage(data) {
        const isMine = data.is_mine || parseInt(data.expediteur_id) === parseInt(myUserId);
        const div = document.createElement('div');
        div.className = `msg-bubble ${isMine ? 'mine' : 'theirs'}`;
        div.innerHTML = `
            <div class="msg-content">${escapeHtml(data.contenu)}</div>
            <span class="msg-time">${formatTime(data.date_envoi)}</span>
        `;
        chatBox.appendChild(div);
    }

    function escapeHtml(str) {
        const d = document.createElement('div');
        d.appendChild(document.createTextNode(str || ''));
        return d.innerHTML;
    }

    function formatTime(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    }

    // ── Delete Message ──────────────────────────────────────
    document.querySelectorAll('.btn-delete-msg').forEach(btn => {
        btn.addEventListener('click', () => {
            const msgId = btn.dataset.msgId;
            const target = btn.dataset.target; // 'moi' ou 'tous'
            if (!confirm('Supprimer ce message ?')) return;

            fetch(`/api/messages/${msgId}/supprimer`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target }),
            }).then(r => r.json()).then(data => {
                if (data.ok) {
                    btn.closest('.msg-bubble').remove();
                }
            });
        });
    });

    // ── Typing Indicator ────────────────────────────────────
    if (msgInput && socket) {
        let typingTimeout;
        msgInput.addEventListener('input', () => {
            socket.emit('en_cours_frappe', { conv_id: convId });
            clearTimeout(typingTimeout);
            typingTimeout = setTimeout(() => {
                socket.emit('arret_frappe', { conv_id: convId });
            }, 1500);
        });

        socket.on('indicateur_frappe', (data) => {
            if (parseInt(data.conv_id) === parseInt(convId) && parseInt(data.user_id) !== parseInt(myUserId)) {
                showTypingIndicator();
            }
        });

        socket.on('arret_indicateur_frappe', (data) => {
            if (parseInt(data.conv_id) === parseInt(convId)) {
                hideTypingIndicator();
            }
        });
    }

    function showTypingIndicator() {
        let ind = document.getElementById('typingIndicator');
        if (!ind) {
            ind = document.createElement('div');
            ind.id = 'typingIndicator';
            ind.className = 'typing-indicator';
            ind.innerHTML = '<span></span><span></span><span></span>';
            chatBox.appendChild(ind);
            scrollToBottom();
        }
    }

    function hideTypingIndicator() {
        const ind = document.getElementById('typingIndicator');
        if (ind) ind.remove();
    }

})();
