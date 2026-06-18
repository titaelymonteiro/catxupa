// app.js _ Utilitarios globais partilhados entre paginas

const API_URL = "http://127.0.0.1:8000";

function getToken() {
    return localStorage.getItem("token");
}

function authHeaders() {
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + getToken()
    };
}
function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

function protegerPagina() {
    if (!getToken()) {
        window.location.href = "login.html";
    }
}

// ── MODERNA SIDEBAR LOGIC ──
function initSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const toggle = document.querySelector('.menu-toggle');
    const content = document.querySelector('.main-content');

    // Create overlay for mobile if it doesn't exist
    if (!document.querySelector('.sidebar-overlay')) {
        const overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        document.body.appendChild(overlay);

        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            document.body.style.overflow = '';
        });
    }

    if (toggle) {
        toggle.addEventListener('click', () => {
            if (window.innerWidth > 992) {
                // Desktop toggle (collapse)
                sidebar.classList.toggle('collapsed');
            } else {
                // Mobile toggle (drawer)
                sidebar.classList.toggle('open');
                document.body.style.overflow = sidebar.classList.contains('open') ? 'hidden' : '';
            }
        });
    }
}

// Auto-init on load
document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
});
