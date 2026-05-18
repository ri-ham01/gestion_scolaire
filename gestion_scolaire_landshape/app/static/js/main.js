/**
 * EduNova — Main JS
 * UI interactions, Command Palette, and accessibility
 */

document.addEventListener("DOMContentLoaded", () => {
    // ── Hamburger Menu ──────────────────────────────────────
    const hamburger = document.getElementById('hamburger');
    const navLinks = document.getElementById('navLinks');

    if (hamburger && navLinks) {
        hamburger.addEventListener('click', () => {
            const isExpanded = hamburger.getAttribute('aria-expanded') === 'true';
            hamburger.setAttribute('aria-expanded', !isExpanded);
            hamburger.classList.toggle('active');
            navLinks.classList.toggle('active');
        });
    }

    // ── Lang Switcher ───────────────────────────────────────
    const langToggle = document.getElementById('langToggle');
    const langDropdown = document.getElementById('langDropdown');

    if (langToggle && langDropdown) {
        langToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isExpanded = langToggle.getAttribute('aria-expanded') === 'true';
            closeAllDropdowns();
            langToggle.setAttribute('aria-expanded', !isExpanded);
            langDropdown.classList.toggle('active');
        });
    }

    // ── User Menu ───────────────────────────────────────────
    const userMenuToggle = document.getElementById('userMenuToggle');
    const userDropdown = document.getElementById('userDropdown');

    if (userMenuToggle && userDropdown) {
        userMenuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isExpanded = userMenuToggle.getAttribute('aria-expanded') === 'true';
            closeAllDropdowns();
            userMenuToggle.setAttribute('aria-expanded', !isExpanded);
            userDropdown.classList.toggle('active');
        });
    }

    // Close dropdowns on outside click
    document.addEventListener('click', () => {
        closeAllDropdowns();
    });

    function closeAllDropdowns() {
        if (langToggle) langToggle.setAttribute('aria-expanded', 'false');
        if (langDropdown) langDropdown.classList.remove('active');
        if (userMenuToggle) userMenuToggle.setAttribute('aria-expanded', 'false');
        if (userDropdown) userDropdown.classList.remove('active');

        // Notifications are handled in notifications.js, but we close them here too if they exist
        const notifToggle = document.getElementById('notifToggle');
        const notifPanel = document.getElementById('notifPanel');
        if (notifToggle) notifToggle.classList.remove('active');
        if (notifPanel) notifPanel.classList.remove('active');
    }

    // ── Command Palette (Ctrl+K) ───────────────────────────
    const cmdOverlay = document.getElementById('cmdOverlay');
    const cmdInput = document.getElementById('cmdInput');
    const cmdResults = document.getElementById('cmdResults');

    if (cmdOverlay && cmdInput && window.EDUNOVA_URLS) {
        // Base actions
        let actions = [
            { title: "Accueil", icon: "fa-house", url: window.EDUNOVA_URLS.home },
            { title: "Emploi du temps public", icon: "fa-calendar-days", url: window.EDUNOVA_URLS.edt },
            { title: "Examens", icon: "fa-file-circle-question", url: window.EDUNOVA_URLS.exam },
            { title: "Annonces", icon: "fa-bullhorn", url: window.EDUNOVA_URLS.annonces },
        ];

        if (window.EDUNOVA_ROLE !== 'public') {
            actions.unshift({ title: "Tableau de bord (" + window.EDUNOVA_ROLE + ")", icon: "fa-gauge-high", url: window.EDUNOVA_URLS.dashboard });
        }

        if (window.EDUNOVA_ROLE === 'professeur') {
            actions.push({ title: "Saisir les notes", icon: "fa-pen-to-square", url: window.EDUNOVA_URLS.notes });
            actions.push({ title: "Faire l'appel (Présences)", icon: "fa-calendar-check", url: window.EDUNOVA_URLS.presences });
            actions.push({ title: "Messagerie (Chat)", icon: "fa-message", url: window.EDUNOVA_URLS.chat });
        }

        // Toggle Palette
        const togglePalette = () => {
            const isHidden = cmdOverlay.getAttribute('aria-hidden') === 'true';
            if (isHidden) {
                cmdOverlay.setAttribute('aria-hidden', 'false');
                cmdOverlay.classList.add('active');
                cmdInput.value = '';
                renderCmdResults(actions);
                setTimeout(() => cmdInput.focus(), 100);
            } else {
                cmdOverlay.setAttribute('aria-hidden', 'true');
                cmdOverlay.classList.remove('active');
                cmdInput.blur();
            }
        };

        // Keyboard Shortcut (Ctrl+K or Cmd+K)
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                togglePalette();
            }
            if (e.key === 'Escape' && cmdOverlay.classList.contains('active')) {
                togglePalette();
            }
        });

        // Close on background click
        cmdOverlay.addEventListener('click', (e) => {
            if (e.target === cmdOverlay) {
                togglePalette();
            }
        });

        // Search logic
        cmdInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const filtered = actions.filter(a => a.title.toLowerCase().includes(query));
            renderCmdResults(filtered);
        });

        function renderCmdResults(results) {
            if (results.length === 0) {
                cmdResults.innerHTML = `<div class="cmd-empty">Aucun résultat trouvé.</div>`;
                return;
            }
            cmdResults.innerHTML = results.map(a => `
                <a href="${a.url}" class="cmd-item">
                    <i class="fa-solid ${a.icon}"></i>
                    <span>${a.title}</span>
                </a>
            `).join('');
        }
    }

    // ── Flash Auto-Dismiss ─────────────────────────────────
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            flash.style.transform = 'translateY(-10px)';
            setTimeout(() => flash.remove(), 300);
        }, 5000); // 5 seconds
    });
});
