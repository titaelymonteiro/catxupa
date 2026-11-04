// app.js — Utilitários globais partilhados entre páginas

// ── MODO ESCURO ─────────────────────────────────────────────────────────────
// Aplicado o mais cedo possível (antes do body ser desenhado) para evitar
// um "flash" do tema claro antes de mudar para escuro.
(function () {
    const preferido = localStorage.getItem("tema") || "claro";
    if (preferido === "escuro") {
        document.documentElement.setAttribute("data-theme", "dark");
    }
})();

function alternarTema() {
    const escuroAtivo = document.documentElement.getAttribute("data-theme") === "dark";
    if (escuroAtivo) {
        document.documentElement.removeAttribute("data-theme");
        localStorage.setItem("tema", "claro");
    } else {
        document.documentElement.setAttribute("data-theme", "dark");
        localStorage.setItem("tema", "escuro");
    }
    atualizarBotaoTema();
}

function atualizarBotaoTema() {
    const btn = document.querySelector(".theme-toggle");
    if (!btn) return;
    const escuroAtivo = document.documentElement.getAttribute("data-theme") === "dark";
    btn.innerText = escuroAtivo ? "☀️ Claro" : "🌙 Escuro";
}

function injetarBotaoTema() {
    const navbar = document.querySelector(".main-navbar > div:last-child");
    if (!navbar || document.querySelector(".theme-toggle")) return;
    const btn = document.createElement("button");
    btn.className = "theme-toggle";
    btn.onclick = alternarTema;
    navbar.insertBefore(btn, navbar.firstChild);
    atualizarBotaoTema();
}

// ── SINO DE NOTIFICAÇÕES ────────────────────────────────────────────────────
let _intervaloNotificacoes = null;

function injetarSinoNotificacoes() {
    const navbar = document.querySelector(".main-navbar > div:last-child");
    if (!navbar || document.querySelector(".sino-wrap") || typeof API_URL === "undefined") return;

    const token = localStorage.getItem("token");
    if (!token) return;

    const wrap = document.createElement("div");
    wrap.className = "sino-wrap";
    wrap.innerHTML = `
        <button class="sino-botao" id="sinoBotao" title="Notificações">
            🔔<span class="sino-badge d-none" id="sinoBadge">0</span>
        </button>
        <div class="sino-painel d-none" id="sinoPainel">
            <div class="sino-painel-topo">
                <span>Notificações</span>
                <button id="sinoMarcarTodas">Marcar todas como lidas</button>
            </div>
            <div class="sino-lista" id="sinoLista"></div>
        </div>
    `;
    navbar.insertBefore(wrap, navbar.firstChild);

    document.getElementById("sinoBotao").addEventListener("click", (e) => {
        e.stopPropagation();
        const painel = document.getElementById("sinoPainel");
        const estavaEscondido = painel.classList.contains("d-none");
        painel.classList.toggle("d-none");
        if (estavaEscondido) carregarListaNotificacoes();
    });

    document.addEventListener("click", (e) => {
        const painel = document.getElementById("sinoPainel");
        if (painel && !painel.classList.contains("d-none") && !wrap.contains(e.target)) {
            painel.classList.add("d-none");
        }
    });

    document.getElementById("sinoMarcarTodas").addEventListener("click", async (e) => {
        e.stopPropagation();
        await fetch(`${API_URL}/notificacoes/marcar-todas-lidas`, {
            method: "PUT",
            headers: { "Authorization": "Bearer " + token }
        });
        atualizarContagemNotificacoes();
        carregarListaNotificacoes();
    });

    // Gera alertas de stock/validade uma vez ao entrar (o polling depois
    // mostra as notificacoes novas). Falha em silencio (ex.: perfil cliente).
    verificarAlertas().finally(atualizarContagemNotificacoes);
    _intervaloNotificacoes = setInterval(atualizarContagemNotificacoes, 20000);
}

async function verificarAlertas() {
    const token = localStorage.getItem("token");
    if (!token || typeof API_URL === "undefined") return;
    try {
        await fetch(`${API_URL}/alertas/verificar`, {
            method: "POST",
            headers: { "Authorization": "Bearer " + token }
        });
    } catch (err) { /* silencioso */ }
}

async function atualizarContagemNotificacoes() {
    const token = localStorage.getItem("token");
    if (!token) return;
    try {
        const res = await fetch(`${API_URL}/notificacoes/contagem`, {
            headers: { "Authorization": "Bearer " + token }
        });
        if (!res.ok) return;
        const data = await res.json();
        const badge = document.getElementById("sinoBadge");
        if (!badge) return;
        if (data.nao_lidas > 0) {
            badge.innerText = data.nao_lidas > 9 ? "9+" : data.nao_lidas;
            badge.classList.remove("d-none");
        } else {
            badge.classList.add("d-none");
        }
    } catch (err) { /* silencioso -- nao interromper a pagina por causa disto */ }
}

async function carregarListaNotificacoes() {
    const token = localStorage.getItem("token");
    const lista = document.getElementById("sinoLista");
    lista.innerHTML = "<div class='sino-vazio'>A carregar...</div>";

    try {
        const res = await fetch(`${API_URL}/notificacoes?limite=15`, {
            headers: { "Authorization": "Bearer " + token }
        });
        if (!res.ok) { lista.innerHTML = "<div class='sino-vazio'>Erro ao carregar.</div>"; return; }

        const notificacoes = await res.json();
        if (!notificacoes.length) {
            lista.innerHTML = "<div class='sino-vazio'>Sem notificações.</div>";
            return;
        }

        lista.innerHTML = notificacoes.map(n => `
            <div class="sino-item ${n.lida ? '' : 'sino-item-nao-lida'}" data-id="${n.id}" data-link="${n.link || ''}">
                <div class="sino-item-msg">${n.mensagem}</div>
                <div class="sino-item-tempo">${formatarTempoRelativo(n.criado_em)}</div>
            </div>
        `).join("");

        lista.querySelectorAll(".sino-item").forEach(el => {
            el.addEventListener("click", async () => {
                const id = el.getAttribute("data-id");
                const link = el.getAttribute("data-link");
                await fetch(`${API_URL}/notificacoes/${id}/lida`, {
                    method: "PUT",
                    headers: { "Authorization": "Bearer " + token }
                });
                atualizarContagemNotificacoes();
                if (link) window.location.href = link;
            });
        });
    } catch (err) {
        lista.innerHTML = "<div class='sino-vazio'>Erro de ligação.</div>";
    }
}

function formatarTempoRelativo(isoStr) {
    if (!isoStr) return "";
    const agora = new Date();
    const data = new Date(isoStr.replace(" ", "T") + "Z");
    const diffMin = Math.round((agora - data) / 60000);
    if (diffMin < 1) return "agora mesmo";
    if (diffMin < 60) return `há ${diffMin} min`;
    const diffH = Math.round(diffMin / 60);
    if (diffH < 24) return `há ${diffH}h`;
    return `há ${Math.round(diffH / 24)}d`;
}

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
    localStorage.removeItem("perfil");
    localStorage.removeItem("nome");
    window.location.href = "login.html";
}

function protegerPagina() {
    if (!getToken()) {
        window.location.href = "login.html";
    }
}

// Sidebar toggle (mobile)
document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector(".menu-toggle");
    const sidebar = document.querySelector(".sidebar");
    if (toggle && sidebar) {
        toggle.addEventListener("click", () => {
            sidebar.classList.toggle("show");
        });
    }

    // ── Ajustar o menu/acesso conforme o perfil ──────────────────────────
    const perfil = localStorage.getItem("perfil");

    // Um cliente nao deve estar no backoffice (paginas com menu lateral):
    // se lá chegar pelo endereço, é reenviado para o portal.
    if (perfil === "cliente" && sidebar) {
        window.location.href = "portal.html";
        return;
    }

    // "Utilizadores" é uma area só de administrador: esconde o link do menu
    // para os funcionarios (o backend ja bloqueia, isto alinha a experiencia).
    if (perfil && perfil !== "admin") {
        document.querySelectorAll('.sidebar-nav a[href="usuarios.html"]').forEach(a => {
            const li = a.closest("li");
            if (li) li.style.display = "none";
        });
        // Se tentar abrir a pagina pelo endereço, reenvia para o dashboard.
        if (location.pathname.endsWith("usuarios.html")) {
            window.location.href = "dashboard.html";
            return;
        }
    }

    criarModalConfirmacao();
    injetarBotaoTema();
    injetarSinoNotificacoes();
});

// ── PAGINAÇÃO REUTILIZÁVEL ─────────────────────────────────────────────────
// Uso em cada página: manter uma variável `paginaAtual` e uma função global
// `irParaPagina(p)` que volta a chamar o render com a página pedida.
// HTML esperado: <div class="pagination-bar" id="paginacaoBar"><div id="paginacaoInfo"></div><div id="paginacaoBotoes"></div></div>

function fatiarPagina(lista, paginaAtual, itensPorPagina) {
    const totalPaginas = Math.max(1, Math.ceil(lista.length / itensPorPagina));
    const pagina = Math.min(Math.max(1, paginaAtual), totalPaginas);
    const inicio = (pagina - 1) * itensPorPagina;
    return {
        paginaAtual: pagina,
        totalPaginas,
        itens: lista.slice(inicio, inicio + itensPorPagina)
    };
}

function renderPaginacao(totalItens, paginaAtual, totalPaginas, itensPorPagina, nomePlural) {
    const bar = document.getElementById("paginacaoBar");
    if (!bar) return;
    if (totalPaginas <= 1) { bar.style.display = "none"; return; }
    bar.style.display = "flex";

    const inicio = (paginaAtual - 1) * itensPorPagina + 1;
    const fim = Math.min(paginaAtual * itensPorPagina, totalItens);
    document.getElementById("paginacaoInfo").innerText =
        `A mostrar ${inicio}–${fim} de ${totalItens} ${nomePlural}`;

    let botoes = `<button class="btn btn-outline-secondary btn-sm" ${paginaAtual === 1 ? "disabled" : ""} onclick="irParaPagina(${paginaAtual - 1})">‹</button>`;
    for (let p = 1; p <= totalPaginas; p++) {
        botoes += `<button class="btn btn-sm ${p === paginaAtual ? "btn-primary" : "btn-outline-secondary"}" onclick="irParaPagina(${p})">${p}</button>`;
    }
    botoes += `<button class="btn btn-outline-secondary btn-sm" ${paginaAtual === totalPaginas ? "disabled" : ""} onclick="irParaPagina(${paginaAtual + 1})">›</button>`;
    document.getElementById("paginacaoBotoes").innerHTML = botoes;
}
// Substitui o confirm() feio do browser por um modal bonito do Bootstrap.
// Uso: confirmarAcao("Apagar medicamento?", "Tens a certeza...?").then(ok => { if (ok) { ... } })

function criarModalConfirmacao() {
    if (document.getElementById("modalConfirmacaoGlobal")) return;

    const modalHtml = `
    <div class="modal fade" id="modalConfirmacaoGlobal" tabindex="-1">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-body text-center py-4">
                    <div style="font-size:2.6rem;" id="confirmIcone">⚠️</div>
                    <h5 class="fw-bold mt-2 mb-1" id="confirmTitulo">Confirmar ação</h5>
                    <p class="text-muted mb-0" id="confirmTexto">Tens a certeza?</p>
                </div>
                <div class="modal-footer justify-content-center border-0 pb-4">
                    <button type="button" class="btn btn-outline-secondary px-4" data-bs-dismiss="modal" id="confirmCancelar">Cancelar</button>
                    <button type="button" class="btn btn-danger px-4" id="confirmOk">Confirmar</button>
                </div>
            </div>
        </div>
    </div>`;
    document.body.insertAdjacentHTML("beforeend", modalHtml);
}

function confirmarAcao(titulo, texto, opts = {}) {
    return new Promise((resolve) => {
        const modalEl = document.getElementById("modalConfirmacaoGlobal");
        document.getElementById("confirmTitulo").innerText = titulo;
        document.getElementById("confirmTexto").innerText = texto;
        document.getElementById("confirmIcone").innerText = opts.icone || "⚠️";

        const btnOk = document.getElementById("confirmOk");
        btnOk.className = `btn px-4 ${opts.tipo === "perigo" ? "btn-danger" : "btn-primary"}`;
        btnOk.innerText = opts.textoOk || "Confirmar";

        const modal = new bootstrap.Modal(modalEl);

        const onConfirm = () => {
            modal.hide();
            resolve(true);
            cleanup();
        };
        const onCancel = () => {
            resolve(false);
            cleanup();
        };
        function cleanup() {
            btnOk.removeEventListener("click", onConfirm);
            modalEl.removeEventListener("hidden.bs.modal", onCancel);
        }

        btnOk.addEventListener("click", onConfirm);
        modalEl.addEventListener("hidden.bs.modal", onCancel);

        modal.show();
    });
}

// ── Exportar CSV (descarrega com o token de autenticacao) ────────────────
async function exportarCSV(caminho, nomeFicheiro) {
    const token = localStorage.getItem("token");
    if (!token || typeof API_URL === "undefined") return;
    try {
        const res = await fetch(`${API_URL}${caminho}`, {
            headers: { "Authorization": "Bearer " + token }
        });
        if (!res.ok) {
            alert(res.status === 403 ? "Sem permissão para exportar isto." : "Erro ao exportar.");
            return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = nomeFicheiro;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    } catch (err) {
        alert("Erro ao exportar.");
    }
}