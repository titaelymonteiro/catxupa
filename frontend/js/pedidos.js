const token = localStorage.getItem("token");
if (!token) { window.location.href = "login.html"; }

let pedidosTodos = [];
let paginaAtual = 1;
const ITENS_POR_PAGINA = 10;

const ESTADO_BADGE = {
    pendente: "warning",
    confirmado: "info",
    pronto: "primary",
    concluido: "success",
    cancelado: "danger"
};
const ESTADO_TEXTO = {
    pendente: "Pendente",
    confirmado: "Confirmado",
    pronto: "Pronto p/ Levantamento",
    concluido: "Concluído",
    cancelado: "Cancelado"
};
// Para cada estado atual, quais os proximos estados possiveis (fluxo do pedido)
const PROXIMOS_ESTADOS = {
    pendente: ["confirmado", "cancelado"],
    confirmado: ["pronto", "cancelado"],
    pronto: ["concluido", "cancelado"],
    concluido: [],
    cancelado: []
};

function mostrarMensagem(texto, tipo = "success") {
    const el = document.getElementById("mensagem");
    el.className = `alert alert-${tipo}`;
    el.innerText = texto;
    el.classList.remove("d-none");
    setTimeout(() => el.classList.add("d-none"), 4000);
}

function renderSkeleton() {
    let html = "";
    for (let i = 0; i < 6; i++) {
        html += `<tr class="skeleton-row">
            <td><div class="skeleton-bar" style="width:30px;"></div></td>
            <td><div class="skeleton-bar" style="width:120px;"></div></td>
            <td><div class="skeleton-bar" style="width:90px;"></div></td>
            <td><div class="skeleton-bar" style="width:160px;"></div></td>
            <td><div class="skeleton-bar" style="width:70px;"></div></td>
            <td><div class="skeleton-bar" style="width:80px;"></div></td>
            <td><div class="skeleton-bar" style="width:100px;"></div></td>
        </tr>`;
    }
    document.getElementById("tabela").innerHTML = html;
}

async function carregar() {
    renderSkeleton();
    try {
        const res = await fetch(`${API_URL}/pedidos`, {
            headers: { "Authorization": "Bearer " + token }
        });
        if (res.status === 401) { window.location.href = "login.html"; return; }

        pedidosTodos = await res.json();
        paginaAtual = 1;
        renderTabela();
    } catch (err) {
        console.error(err);
        mostrarMensagem("Erro de ligação com o servidor.", "danger");
    }
}

function irParaPagina(p) {
    paginaAtual = p;
    renderTabela();
}

function renderTabela() {
    const filtro = document.getElementById("filtroEstado").value;
    const lista = filtro ? pedidosTodos.filter(p => p.estado === filtro) : pedidosTodos;

    if (!lista.length) {
        document.getElementById("tabela").innerHTML =
            "<tr><td colspan='7' class='text-center text-muted py-4'>Nenhum pedido encontrado.</td></tr>";
        document.getElementById("paginacaoBar").style.display = "none";
        return;
    }

    const { paginaAtual: pag, totalPaginas, itens } = fatiarPagina(lista, paginaAtual, ITENS_POR_PAGINA);
    paginaAtual = pag;

    document.getElementById("tabela").innerHTML = itens.map(p => {
        const itensTexto = p.itens.map(i => `${i.quantidade}× ${i.medicamento_nome}`).join(", ");
        return `
        <tr>
            <td class="text-muted small">#${p.id}</td>
            <td class="fw-semibold">${p.cliente_nome}</td>
            <td class="small">${p.criado_em ? p.criado_em.substring(0, 16).replace("T", " ") : "—"}</td>
            <td class="small">${itensTexto}</td>
            <td class="fw-bold">${parseFloat(p.total).toLocaleString("pt-CV")} CVE</td>
            <td><span class="badge bg-${ESTADO_BADGE[p.estado] || "secondary"}">${ESTADO_TEXTO[p.estado] || p.estado}</span></td>
            <td>
                <button class="btn btn-outline-primary btn-sm" onclick="abrirDetalhes(${p.id})">Ver / Gerir</button>
            </td>
        </tr>`;
    }).join("");

    renderPaginacao(lista.length, paginaAtual, totalPaginas, ITENS_POR_PAGINA, "pedidos");
}

function abrirDetalhes(pedidoId) {
    const p = pedidosTodos.find(x => x.id === pedidoId);
    if (!p) return;
    window._pedidoDetalhe = p;

    const itensHtml = p.itens.map(i => `
        <tr>
            <td>${i.medicamento_nome}</td>
            <td>${i.quantidade}</td>
            <td>${parseFloat(i.preco_unitario).toLocaleString("pt-CV")} CVE</td>
            <td class="fw-bold">${parseFloat(i.subtotal).toLocaleString("pt-CV")} CVE</td>
        </tr>
    `).join("");

    const linkMapa = (p.entrega_lat != null && p.entrega_lng != null)
        ? `https://www.google.com/maps/search/?api=1&query=${p.entrega_lat},${p.entrega_lng}`
        : (p.morada_entrega ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(p.morada_entrega)}` : null);

    const blocoEntrega = p.morada_entrega
        ? `<p><strong>📍 Entrega:</strong> ${p.morada_entrega}
             ${linkMapa ? ` — <a href="${linkMapa}" target="_blank" rel="noopener">ver no mapa ↗</a>` : ""}</p>`
        : "";

    const nomeMetodo = { vinti4: "Vinti4", visa: "Visa" };
    const blocoPagamento = p.metodo_pagamento
        ? `<p><strong>💳 Pagamento:</strong> <span class="badge bg-success">Pago</span> — ${nomeMetodo[p.metodo_pagamento] || p.metodo_pagamento}${p.cartao_ultimos4 ? ` (•••• ${p.cartao_ultimos4})` : ""}</p>`
        : `<p><strong>💳 Pagamento:</strong> <span class="badge bg-secondary">Não pago</span></p>`;

    document.getElementById("modalDetalhesBody").innerHTML = `
        <p><strong>Cliente:</strong> ${p.cliente_nome} (${p.cliente_email})</p>
        <p><strong>Estado atual:</strong> <span class="badge bg-${ESTADO_BADGE[p.estado]}">${ESTADO_TEXTO[p.estado]}</span></p>
        ${blocoPagamento}
        ${blocoEntrega}
        ${p.nota ? `<p><strong>Nota:</strong> ${p.nota}</p>` : ""}
        <table class="table table-sm table-bordered">
            <thead class="table-light">
                <tr><th>Medicamento</th><th>Qtd.</th><th>Preço</th><th>Subtotal</th></tr>
            </thead>
            <tbody>${itensHtml}</tbody>
            <tfoot>
                <tr class="table-primary fw-bold">
                    <td colspan="3" class="text-end">Total:</td>
                    <td>${parseFloat(p.total).toLocaleString("pt-CV")} CVE</td>
                </tr>
            </tfoot>
        </table>
    `;

    const proximos = PROXIMOS_ESTADOS[p.estado] || [];
    const botoes = proximos.map(estado => {
        const cor = estado === "cancelado" ? "outline-danger" : "primary";
        return `<button class="btn btn-${cor} btn-sm" onclick="mudarEstado(${p.id}, '${estado}')">${ESTADO_TEXTO[estado]}</button>`;
    }).join(" ");

    document.getElementById("modalDetalhesAcoes").innerHTML = `
        <button class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
        <button class="btn btn-outline-secondary" onclick="imprimirTalaoPedido(window._pedidoDetalhe)">🖨️ Talão</button>
        ${botoes}
    `;

    new bootstrap.Modal(document.getElementById("modalDetalhes")).show();
}

async function mudarEstado(pedidoId, novoEstado) {
    const res = await fetch(`${API_URL}/pedidos/${pedidoId}/estado`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
        body: JSON.stringify({ estado: novoEstado })
    });
    const data = await res.json();

    if (res.ok) {
        bootstrap.Modal.getInstance(document.getElementById("modalDetalhes")).hide();
        mostrarMensagem(data.mensagem || "Pedido atualizado.");
        carregar();
    } else {
        mostrarMensagem(data.detail || "Erro ao atualizar o pedido.", "danger");
    }
}

if (token) carregar();