const token = localStorage.getItem("token");
if (!token) { window.location.href = "login.html"; }

let logsAtuais = [];
let paginaAtual = 1;
const ITENS_POR_PAGINA = 10;

function mostrarMensagem(texto, tipo = "success") {
    const el = document.getElementById("mensagem");
    el.className = `alert alert-${tipo}`;
    el.innerText = texto;
    el.classList.remove("d-none");
    setTimeout(() => el.classList.add("d-none"), 4000);
}

function corDaAcao(acao) {
    switch (acao) {
        case "criar": return "success";
        case "editar": return "warning";
        case "apagar": return "danger";
        case "anular": return "danger";
        default: return "secondary";
    }
}

function formatarData(iso) {
    if (!iso) return "—";
    return iso.substring(0, 16).replace("T", " ");
}

function renderSkeleton() {
    let html = "";
    for (let i = 0; i < 6; i++) {
        html += `<tr class="skeleton-row">
            <td><div class="skeleton-bar" style="width:120px;"></div></td>
            <td><div class="skeleton-bar" style="width:70px;"></div></td>
            <td><div class="skeleton-bar" style="width:90px;"></div></td>
            <td><div class="skeleton-bar" style="width:220px;"></div></td>
            <td><div class="skeleton-bar" style="width:140px;"></div></td>
        </tr>`;
    }
    document.getElementById("tabela").innerHTML = html;
}

async function carregar() {
    renderSkeleton();

    const entidade = document.getElementById("filtroEntidade").value;
    const limite = document.getElementById("filtroLimite").value;

    let url = `${API_URL}/logs?limite=${limite}`;

    try {
        const res = await fetch(url, {
            headers: { "Authorization": "Bearer " + token }
        });

        if (res.status === 401) { window.location.href = "login.html"; return; }

        if (res.status === 403) {
            document.getElementById("areaConteudo").classList.add("d-none");
            document.querySelector(".d-flex.gap-2").classList.add("d-none");
            document.getElementById("semPermissao").classList.remove("d-none");
            return;
        }

        let logs = await res.json();

        if (entidade) {
            logs = logs.filter(l => l.entidade === entidade);
        }

        logsAtuais = logs;
        paginaAtual = 1;
        renderTabela(logs);

    } catch (err) {
        console.error(err);
        mostrarMensagem("Erro de ligação com o servidor.", "danger");
    }
}

function renderTabela(logs) {
    if (!logs.length) {
        document.getElementById("tabela").innerHTML =
            "<tr><td colspan='5' class='text-center text-muted py-4'>Sem registos para mostrar.</td></tr>";
        document.getElementById("paginacaoBar").style.display = "none";
        return;
    }

    const { paginaAtual: pag, totalPaginas, itens } = fatiarPagina(logs, paginaAtual, ITENS_POR_PAGINA);
    paginaAtual = pag;

    document.getElementById("tabela").innerHTML = itens.map(l => `
        <tr>
            <td class="text-muted small">${formatarData(l.criado_em)}</td>
            <td><span class="badge bg-${corDaAcao(l.acao)}">${l.acao}</span></td>
            <td class="text-capitalize">${l.entidade} <span class="text-muted small">#${l.entidade_id}</span></td>
            <td>${l.descricao || "—"}</td>
            <td class="small">${l.usuario_email}</td>
        </tr>
    `).join("");

    renderPaginacao(logs.length, paginaAtual, totalPaginas, ITENS_POR_PAGINA, "registos");
}

function irParaPagina(p) {
    paginaAtual = p;
    renderTabela(logsAtuais);
}

if (token) carregar();