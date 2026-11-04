const token = localStorage.getItem("token");
if (!token) { window.location.href = "login.html"; }

let fornecedoresTodos = [];
let paginaAtual = 1;
const ITENS_POR_PAGINA = 8;

// ── Mapas-seletor de localizacao (adicionar + editar) ────────────────────
let selMapaAdd = null, selMapaEdit = null;

function _marcadoTexto(idTexto, lat, lng, guardado = false) {
    document.getElementById(idTexto).innerHTML =
        `<span class="text-success fw-bold">✓ ${guardado ? "Ponto guardado" : "Ponto marcado"}</span> (${(+lat).toFixed(6)}, ${(+lng).toFixed(6)})`;
}
function _numOuNull(id) {
    const v = document.getElementById(id).value;
    return v ? parseFloat(v) : null;
}

document.addEventListener("DOMContentLoaded", () => {
    const formAdd = document.getElementById("formAdicionar");
    if (formAdd) formAdd.addEventListener("shown.bs.collapse", () => {
        if (!selMapaAdd) {
            selMapaAdd = iniciarMapaSeletor("mapaAdd", (lat, lng) => {
                document.getElementById("lat").value = (+lat).toFixed(6);
                document.getElementById("lng").value = (+lng).toFixed(6);
                _marcadoTexto("coordAdd", lat, lng);
            });
        } else {
            selMapaAdd.mapa.invalidateSize();
        }
    });

    const modalEd = document.getElementById("modalEditar");
    if (modalEd) modalEd.addEventListener("shown.bs.modal", () => {
        const f = window._fornecedores[document.getElementById("editId").value] || {};
        const temCoords = (f.latitude != null && f.longitude != null);
        if (!selMapaEdit) {
            selMapaEdit = iniciarMapaSeletor("mapaEdit", (lat, lng) => {
                document.getElementById("editLat").value = (+lat).toFixed(6);
                document.getElementById("editLng").value = (+lng).toFixed(6);
                _marcadoTexto("coordEdit", lat, lng);
            }, temCoords ? { marcador: { lat: f.latitude, lng: f.longitude } } : {});
        } else {
            selMapaEdit.mapa.invalidateSize();
            if (temCoords) selMapaEdit.colocar(f.latitude, f.longitude, false);
            else selMapaEdit.limpar();
        }
        if (temCoords) {
            document.getElementById("editLat").value = (+f.latitude).toFixed(6);
            document.getElementById("editLng").value = (+f.longitude).toFixed(6);
            _marcadoTexto("coordEdit", f.latitude, f.longitude, true);
        } else {
            document.getElementById("editLat").value = "";
            document.getElementById("editLng").value = "";
            document.getElementById("coordEdit").textContent = "Nenhum ponto marcado.";
        }
    });
});

function mostrarMensagem(texto, tipo = "success") {
    const el = document.getElementById("mensagem");
    el.className = `alert alert-${tipo}`;
    el.innerText = texto;
    el.classList.remove("d-none");
    setTimeout(() => el.classList.add("d-none"), 4000);
}

function renderSkeleton() {
    let html = "";
    for (let i = 0; i < 5; i++) {
        html += `<tr class="skeleton-row">
            <td><div class="skeleton-bar" style="width:30px;"></div></td>
            <td><div class="skeleton-bar" style="width:140px;"></div></td>
            <td><div class="skeleton-bar" style="width:90px;"></div></td>
            <td><div class="skeleton-bar" style="width:90px;"></div></td>
            <td><div class="skeleton-bar" style="width:120px;"></div></td>
            <td><div class="skeleton-bar" style="width:100px;"></div></td>
            <td><div class="skeleton-bar" style="width:70px;"></div></td>
        </tr>`;
    }
    document.getElementById("tabela").innerHTML = html;
}

async function carregar() {
    renderSkeleton();
    try {
        const res = await fetch(`${API_URL}/fornecedores`, {
            headers: { "Authorization": "Bearer " + token }
        });
        if (res.status === 401) { window.location.href = "login.html"; return; }

        fornecedoresTodos = await res.json();
        window._fornecedores = {};
        fornecedoresTodos.forEach(f => window._fornecedores[f.id] = f);
        paginaAtual = 1;
        renderTabela(fornecedoresTodos);

    } catch (err) {
        console.error(err);
        mostrarMensagem("Erro de ligação com o servidor.", "danger");
    }
}

function renderTabela(lista) {
    if (!lista.length) {
        document.getElementById("tabela").innerHTML =
            "<tr><td colspan='7' class='text-center text-muted py-4'>Nenhum fornecedor encontrado.</td></tr>";
        document.getElementById("paginacaoBar").style.display = "none";
        return;
    }

    const { paginaAtual: pag, totalPaginas, itens } = fatiarPagina(lista, paginaAtual, ITENS_POR_PAGINA);
    paginaAtual = pag;

    document.getElementById("tabela").innerHTML = itens.map(f => `
        <tr>
            <td class="text-muted small">#${f.id}</td>
            <td class="fw-semibold">${f.nome}</td>
            <td>${f.nif || "—"}</td>
            <td>${f.telefone || "—"}</td>
            <td>${f.email || "—"}</td>
            <td>${f.endereco || "—"}</td>
            <td>
                ${(f.endereco || f.latitude != null) ? `<button class="btn btn-outline-secondary btn-sm me-1" onclick="verMoradaNoMapa(window._fornecedores[${f.id}].endereco, window._fornecedores[${f.id}].nome, window._fornecedores[${f.id}].latitude, window._fornecedores[${f.id}].longitude)" title="Ver no mapa">📍</button>` : ""}
                <button class="btn btn-warning btn-sm me-1" onclick="abrirEditar(${f.id})" title="Editar">✏️</button>
                <button class="btn btn-danger btn-sm" onclick="apagar(${f.id})" title="Apagar">🗑️</button>
            </td>
        </tr>
    `).join("");

    renderPaginacao(lista.length, paginaAtual, totalPaginas, ITENS_POR_PAGINA, "fornecedores");
}

function irParaPagina(p) {
    paginaAtual = p;
    const termo = document.getElementById("busca").value.toLowerCase();
    const lista = termo
        ? fornecedoresTodos.filter(f =>
            f.nome.toLowerCase().includes(termo) ||
            (f.nif || "").toLowerCase().includes(termo) ||
            (f.email || "").toLowerCase().includes(termo))
        : fornecedoresTodos;
    renderTabela(lista);
}

function filtrar() {
    paginaAtual = 1;
    const termo = document.getElementById("busca").value.toLowerCase();
    const filtrados = fornecedoresTodos.filter(f =>
        f.nome.toLowerCase().includes(termo) ||
        (f.nif || "").toLowerCase().includes(termo) ||
        (f.email || "").toLowerCase().includes(termo)
    );
    renderTabela(filtrados);
}

async function adicionar() {
    const nome = document.getElementById("nome").value.trim();
    const nif = document.getElementById("nif").value.trim();
    const telefone = document.getElementById("telefone").value.trim();
    const email = document.getElementById("email").value.trim();
    const endereco = document.getElementById("endereco").value.trim();

    if (!nome) {
        mostrarMensagem("O nome é obrigatório.", "warning");
        return;
    }

    const res = await fetch(`${API_URL}/fornecedores`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
        body: JSON.stringify({ nome, nif, telefone, email, endereco,
            latitude: _numOuNull("lat"), longitude: _numOuNull("lng") })
    });

    if (res.ok) {
        mostrarMensagem("Fornecedor criado com sucesso!");
        ["nome", "nif", "telefone", "email", "endereco", "lat", "lng"].forEach(id => document.getElementById(id).value = "");
        document.getElementById("coordAdd").textContent = "Nenhum ponto marcado.";
        if (selMapaAdd) selMapaAdd.limpar();
        document.getElementById("formAdicionar").classList.remove("show");
        carregar();
    } else {
        const data = await res.json();
        mostrarMensagem(data.detail || "Erro ao criar fornecedor.", "danger");
    }
}

function abrirEditar(id) {
    const f = window._fornecedores[id];
    document.getElementById("editId").value = f.id;
    document.getElementById("editNome").value = f.nome;
    document.getElementById("editNif").value = f.nif || "";
    document.getElementById("editTelefone").value = f.telefone || "";
    document.getElementById("editEmail").value = f.email || "";
    document.getElementById("editEndereco").value = f.endereco || "";
    new bootstrap.Modal(document.getElementById("modalEditar")).show();
}

async function guardarEdicao() {
    const id = document.getElementById("editId").value;
    const nome = document.getElementById("editNome").value.trim();
    const nif = document.getElementById("editNif").value.trim();
    const telefone = document.getElementById("editTelefone").value.trim();
    const email = document.getElementById("editEmail").value.trim();
    const endereco = document.getElementById("editEndereco").value.trim();

    const res = await fetch(`${API_URL}/fornecedores/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
        body: JSON.stringify({ nome, nif, telefone, email, endereco,
            latitude: _numOuNull("editLat"), longitude: _numOuNull("editLng") })
    });

    bootstrap.Modal.getInstance(document.getElementById("modalEditar")).hide();

    if (res.ok) {
        mostrarMensagem("Fornecedor atualizado com sucesso!");
        carregar();
    } else {
        mostrarMensagem("Erro ao atualizar fornecedor.", "danger");
    }
}

async function apagar(id) {
    const f = window._fornecedores[id];
    const ok = await confirmarAcao(
        "Apagar fornecedor?",
        `Tens a certeza que queres apagar "${f.nome}"?`,
        { tipo: "perigo", textoOk: "Apagar", icone: "🗑️" }
    );
    if (!ok) return;

    const res = await fetch(`${API_URL}/fornecedores/${id}`, {
        method: "DELETE",
        headers: { "Authorization": "Bearer " + token }
    });

    if (res.ok) {
        mostrarMensagem("Fornecedor removido.");
        carregar();
    } else {
        const data = await res.json();
        mostrarMensagem(data.detail || "Erro ao remover fornecedor.", "danger");
    }
}

if (token) carregar();