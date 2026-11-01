const token = localStorage.getItem("token");
if (!token) { window.location.href = "login.html"; }

let clientesTodos = [];
let paginaAtual = 1;
const ITENS_POR_PAGINA = 8;

// ── Mapas-seletor de localizacao (adicionar + editar) ────────────────────
let selMapaAdd = null, selMapaEdit = null;

function _marcadoTexto(idTexto, lat, lng, guardado = false) {
    document.getElementById(idTexto).innerHTML =
        `<span class="text-success fw-bold">✓ ${guardado ? "Ponto guardado" : "Ponto marcado"}</span> (${(+lat).toFixed(6)}, ${(+lng).toFixed(6)})`;
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
        const c = window._clientes[document.getElementById("editId").value] || {};
        const temCoords = (c.latitude != null && c.longitude != null);
        if (!selMapaEdit) {
            selMapaEdit = iniciarMapaSeletor("mapaEdit", (lat, lng) => {
                document.getElementById("editLat").value = (+lat).toFixed(6);
                document.getElementById("editLng").value = (+lng).toFixed(6);
                _marcadoTexto("coordEdit", lat, lng);
            }, temCoords ? { marcador: { lat: c.latitude, lng: c.longitude } } : {});
        } else {
            selMapaEdit.mapa.invalidateSize();
            if (temCoords) selMapaEdit.colocar(c.latitude, c.longitude, false);
            else selMapaEdit.limpar();
        }
        if (temCoords) {
            document.getElementById("editLat").value = (+c.latitude).toFixed(6);
            document.getElementById("editLng").value = (+c.longitude).toFixed(6);
            _marcadoTexto("coordEdit", c.latitude, c.longitude, true);
        } else {
            document.getElementById("editLat").value = "";
            document.getElementById("editLng").value = "";
            document.getElementById("coordEdit").textContent = "Nenhum ponto marcado.";
        }
    });
});

function _numOuNull(id) {
    const v = document.getElementById(id).value;
    return v ? parseFloat(v) : null;
}

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
        const res = await fetch(`${API_URL}/clientes`, {
            headers: { "Authorization": "Bearer " + token }
        });
        if (res.status === 401) { window.location.href = "login.html"; return; }

        clientesTodos = await res.json();
        window._clientes = {};
        clientesTodos.forEach(c => window._clientes[c.id] = c);
        paginaAtual = 1;
        renderTabela(clientesTodos);

    } catch (err) {
        console.error(err);
        mostrarMensagem("Erro de ligação com o servidor.", "danger");
    }
}

function renderTabela(lista) {
    if (!lista.length) {
        document.getElementById("tabela").innerHTML =
            "<tr><td colspan='6' class='text-center text-muted py-4'>Nenhum cliente encontrado.</td></tr>";
        document.getElementById("paginacaoBar").style.display = "none";
        return;
    }

    const { paginaAtual: pag, totalPaginas, itens } = fatiarPagina(lista, paginaAtual, ITENS_POR_PAGINA);
    paginaAtual = pag;

    document.getElementById("tabela").innerHTML = itens.map(c => `
        <tr>
            <td class="text-muted small">#${c.id}</td>
            <td class="fw-semibold">${c.nome}</td>
            <td>${c.telefone || "—"}</td>
            <td>${c.email || "—"}</td>
            <td>${c.endereco || "—"}</td>
            <td>
                ${(c.endereco || c.latitude != null) ? `<button class="btn btn-outline-secondary btn-sm me-1" onclick="verMoradaNoMapa(window._clientes[${c.id}].endereco, window._clientes[${c.id}].nome, window._clientes[${c.id}].latitude, window._clientes[${c.id}].longitude)" title="Ver no mapa">📍</button>` : ""}
                <button class="btn btn-info btn-sm me-1 text-white" onclick="verHistorico(${c.id})" title="Histórico">🧾</button>
                <button class="btn btn-warning btn-sm me-1" onclick="abrirEditar(${c.id})" title="Editar">✏️</button>
                <button class="btn btn-danger btn-sm" onclick="apagar(${c.id})" title="Apagar">🗑️</button>
            </td>
        </tr>
    `).join("");

    renderPaginacao(lista.length, paginaAtual, totalPaginas, ITENS_POR_PAGINA, "clientes");
}

function irParaPagina(p) {
    paginaAtual = p;
    const termo = document.getElementById("busca").value.toLowerCase();
    const lista = termo
        ? clientesTodos.filter(c =>
            c.nome.toLowerCase().includes(termo) ||
            (c.telefone || "").toLowerCase().includes(termo) ||
            (c.email || "").toLowerCase().includes(termo))
        : clientesTodos;
    renderTabela(lista);
}

function filtrar() {
    paginaAtual = 1;
    const termo = document.getElementById("busca").value.toLowerCase();
    const filtrados = clientesTodos.filter(c =>
        c.nome.toLowerCase().includes(termo) ||
        (c.telefone || "").toLowerCase().includes(termo) ||
        (c.email || "").toLowerCase().includes(termo)
    );
    renderTabela(filtrados);
}

async function adicionar() {
    const nome = document.getElementById("nome").value.trim();
    const telefone = document.getElementById("telefone").value.trim();
    const email = document.getElementById("email").value.trim();
    const endereco = document.getElementById("endereco").value.trim();

    if (!nome) {
        mostrarMensagem("O nome é obrigatório.", "warning");
        return;
    }

    const res = await fetch(`${API_URL}/clientes`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
        body: JSON.stringify({ nome, telefone, email, endereco,
            latitude: _numOuNull("lat"), longitude: _numOuNull("lng") })
    });

    if (res.ok) {
        mostrarMensagem("Cliente criado com sucesso!");
        ["nome", "telefone", "email", "endereco", "lat", "lng"].forEach(id => document.getElementById(id).value = "");
        document.getElementById("coordAdd").textContent = "Nenhum ponto marcado.";
        if (selMapaAdd) selMapaAdd.limpar();
        document.getElementById("formAdicionar").classList.remove("show");
        carregar();
    } else {
        const data = await res.json();
        mostrarMensagem(data.detail || "Erro ao criar cliente.", "danger");
    }
}

function abrirEditar(id) {
    const c = window._clientes[id];
    document.getElementById("editId").value = c.id;
    document.getElementById("editNome").value = c.nome;
    document.getElementById("editTelefone").value = c.telefone || "";
    document.getElementById("editEmail").value = c.email || "";
    document.getElementById("editEndereco").value = c.endereco || "";
    new bootstrap.Modal(document.getElementById("modalEditar")).show();
}

async function guardarEdicao() {
    const id = document.getElementById("editId").value;
    const nome = document.getElementById("editNome").value.trim();
    const telefone = document.getElementById("editTelefone").value.trim();
    const email = document.getElementById("editEmail").value.trim();
    const endereco = document.getElementById("editEndereco").value.trim();

    const res = await fetch(`${API_URL}/clientes/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
        body: JSON.stringify({ nome, telefone, email, endereco,
            latitude: _numOuNull("editLat"), longitude: _numOuNull("editLng") })
    });

    bootstrap.Modal.getInstance(document.getElementById("modalEditar")).hide();

    if (res.ok) {
        mostrarMensagem("Cliente atualizado com sucesso!");
        carregar();
    } else {
        mostrarMensagem("Erro ao atualizar cliente.", "danger");
    }
}

async function verHistorico(id) {
    const c = window._clientes[id];
    const res = await fetch(`${API_URL}/clientes/${id}/historico`, {
        headers: { "Authorization": "Bearer " + token }
    });
    const vendas = await res.json();

    let html = `<p><strong>Cliente:</strong> ${c.nome}</p>`;

    if (!vendas.length) {
        html += `<p class="text-muted">Este cliente ainda não tem compras registadas.</p>`;
    } else {
        const total = vendas.reduce((s, v) => s + v.total, 0);
        html += `
            <table class="table table-sm table-bordered">
                <thead class="table-light">
                    <tr><th>ID</th><th>Total</th><th>Data</th></tr>
                </thead>
                <tbody>
                    ${vendas.map(v => `
                        <tr>
                            <td>#${v.id}</td>
                            <td class="fw-bold text-success">${parseFloat(v.total).toLocaleString("pt-CV")} CVE</td>
                            <td>${v.criado_em ? v.criado_em.substring(0, 16).replace("T", " ") : "—"}</td>
                        </tr>
                    `).join("")}
                </tbody>
                <tfoot>
                    <tr class="table-primary fw-bold">
                        <td colspan="1" class="text-end">Total Gasto:</td>
                        <td colspan="2">${total.toLocaleString("pt-CV")} CVE</td>
                    </tr>
                </tfoot>
            </table>
        `;
    }

    document.getElementById("modalHistoricoBody").innerHTML = html;
    new bootstrap.Modal(document.getElementById("modalHistorico")).show();
}

async function apagar(id) {
    const c = window._clientes[id];
    if (!confirm(`Tens a certeza que queres apagar o cliente "${c.nome}"?`)) return;

    const res = await fetch(`${API_URL}/clientes/${id}`, {
        method: "DELETE",
        headers: { "Authorization": "Bearer " + token }
    });

    if (res.ok) {
        mostrarMensagem("Cliente removido.");
        carregar();
    } else {
        mostrarMensagem("Erro ao remover cliente.", "danger");
    }
}

function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

if (token) carregar();