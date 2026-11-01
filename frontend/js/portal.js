const token = localStorage.getItem("token");
if (!token) { window.location.href = "login.html"; }

let minhaContaId = null;
let catalogoTodos = [];
let carrinho = {};  // { medicamento_id: { nome, preco, quantidade } }

// ── Entrega (morada + ponto no mapa) ─────────────────────────────────────
let entregaCoords = null;   // { lat, lng } quando o cliente marca no mapa
let mapaEntrega = null;     // instancia do mapa (init preguicoso)

document.addEventListener("DOMContentLoaded", () => {
    const area = document.getElementById("areaNovoPedido");
    if (!area) return;
    // O mapa so pode ser criado quando o painel esta visivel (Leaflet precisa
    // de tamanho). Inicia na 1a vez que o painel abre; depois so recalcula.
    area.addEventListener("shown.bs.collapse", () => {
        if (!mapaEntrega) {
            mapaEntrega = iniciarMapaSeletor("mapaEntrega", (lat, lng) => {
                entregaCoords = { lat: +lat.toFixed(6), lng: +lng.toFixed(6) };
                document.getElementById("coordEntrega").innerHTML =
                    `<span class="text-success fw-bold">✓ Ponto marcado</span> (${entregaCoords.lat}, ${entregaCoords.lng})`;
            });
        } else {
            mapaEntrega.mapa.invalidateSize();
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

async function carregarConta() {
    try {
        const res = await fetch(`${API_URL}/minha-conta`, {
            headers: { "Authorization": "Bearer " + token }
        });
        if (res.status === 401) { window.location.href = "login.html"; return; }

        const conta = await res.json();
        minhaContaId = conta.id;
        document.getElementById("saudacao").innerText = `Olá, ${conta.nome}!`;
        document.getElementById("emailConta").innerText = conta.email;

        if (conta.tem_historico) {
            carregarCompras();
        } else {
            document.getElementById("semHistorico").classList.remove("d-none");
        }

        carregarCatalogo();
        carregarMeusPedidos();
        carregarFidelidade();
    } catch (err) {
        console.error(err);
        mostrarMensagem("Erro de ligação com o servidor.", "danger");
    }
}

async function carregarCompras() {
    const res = await fetch(`${API_URL}/minhas-compras`, {
        headers: { "Authorization": "Bearer " + token }
    });

    if (!res.ok) {
        document.getElementById("semHistorico").classList.remove("d-none");
        return;
    }

    const compras = await res.json();

    if (!compras.length) {
        document.getElementById("semHistorico").classList.remove("d-none");
        return;
    }

    document.getElementById("areaCompras").classList.remove("d-none");

    document.getElementById("tabelaCompras").innerHTML = compras.map(v => `
        <tr>
            <td>${v.criado_em ? v.criado_em.substring(0, 16).replace("T", " ") : "—"}</td>
            <td class="fw-bold">${parseFloat(v.total).toLocaleString("pt-CV")} CVE</td>
            <td>${v.anulada ? '<span class="badge bg-danger">Anulada</span>' : '<span class="badge bg-success">Concluída</span>'}</td>
        </tr>
    `).join("");

    const total = compras.filter(v => !v.anulada).reduce((s, v) => s + v.total, 0);
    document.getElementById("totalGasto").innerText = `Total gasto: ${total.toLocaleString("pt-CV")} CVE`;
}

async function alterarPassword() {
    const atual = document.getElementById("passwordAtual").value;
    const nova = document.getElementById("passwordNova").value;
    const confirmar = document.getElementById("passwordConfirmar").value;

    if (!atual || !nova) {
        mostrarMensagem("Preenche a palavra-passe atual e a nova.", "warning");
        return;
    }
    if (nova.length < 4) {
        mostrarMensagem("A nova palavra-passe deve ter pelo menos 4 caracteres.", "warning");
        return;
    }
    if (nova !== confirmar) {
        mostrarMensagem("As palavras-passe novas não coincidem.", "warning");
        return;
    }

    const res = await fetch(`${API_URL}/usuarios/${minhaContaId}/password`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
        body: JSON.stringify({ password_atual: atual, password_nova: nova })
    });

    if (res.ok) {
        mostrarMensagem("Palavra-passe alterada com sucesso!");
        ["passwordAtual", "passwordNova", "passwordConfirmar"].forEach(id => document.getElementById(id).value = "");
    } else {
        const data = await res.json();
        mostrarMensagem(data.detail || "Erro ao alterar a palavra-passe.", "danger");
    }
}

/* ── FIDELIDADE ──────────────────────────────────────────────────────── */
async function carregarFidelidade() {
    const res = await fetch(`${API_URL}/minha-fidelidade`, {
        headers: { "Authorization": "Bearer " + token }
    });
    if (!res.ok) return;

    const dados = await res.json();
    document.getElementById("areaFidelidade").classList.remove("d-none");
    document.getElementById("saldoPontos").innerText = dados.saldo;

    const TIPO_TEXTO = { ganho: "Compra", resgate: "Resgate de desconto", ajuste: "Ajuste" };
    if (!dados.historico.length) {
        document.getElementById("tabelaHistoricoPontos").innerHTML =
            "<tr><td colspan='3' class='text-center text-muted py-3'>Ainda sem movimentos.</td></tr>";
        return;
    }

    document.getElementById("tabelaHistoricoPontos").innerHTML = dados.historico.map(h => `
        <tr>
            <td class="small">${h.criado_em ? h.criado_em.substring(0, 16).replace("T", " ") : "—"}</td>
            <td class="small">${h.motivo || TIPO_TEXTO[h.tipo] || h.tipo}</td>
            <td class="text-end fw-bold ${h.pontos >= 0 ? 'text-success' : 'text-danger'}">${h.pontos >= 0 ? '+' : ''}${h.pontos}</td>
        </tr>
    `).join("");
}

/* ── CATÁLOGO E CARRINHO ─────────────────────────────────────────────── */
async function carregarCatalogo() {
    const res = await fetch(`${API_URL}/catalogo`, {
        headers: { "Authorization": "Bearer " + token }
    });
    if (!res.ok) return;
    catalogoTodos = await res.json();
    renderCatalogo();
}

function renderCatalogo() {
    const termo = document.getElementById("buscaCatalogo").value.toLowerCase();
    const lista = catalogoTodos.filter(m => m.nome.toLowerCase().includes(termo));

    if (!lista.length) {
        document.getElementById("listaCatalogo").innerHTML =
            "<p class='text-muted small text-center py-3 mb-0'>Nenhum medicamento encontrado.</p>";
        return;
    }

    document.getElementById("listaCatalogo").innerHTML = lista.map(m => {
        let badge = "";
        if (m.requer_receita) {
            badge = '<span class="badge bg-dark ms-1">🔒 Exige receita — só na farmácia</span>';
        } else if (!m.disponivel) {
            badge = '<span class="badge bg-secondary ms-1">Indisponível</span>';
        }
        return `
        <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
            <div>
                <div class="fw-semibold small">${m.nome}</div>
                <div class="text-muted" style="font-size:12.5px;">
                    ${m.categoria || "—"} · ${parseFloat(m.preco).toLocaleString("pt-CV")} CVE
                    ${badge}
                </div>
            </div>
            <button class="btn btn-outline-primary btn-sm" ${m.disponivel ? "" : "disabled"} onclick="adicionarAoCarrinho(${m.id})">➕</button>
        </div>`;
    }).join("");
}

function adicionarAoCarrinho(medicamentoId) {
    const item = catalogoTodos.find(m => m.id === medicamentoId);
    if (!item) return;

    if (carrinho[medicamentoId]) {
        carrinho[medicamentoId].quantidade += 1;
    } else {
        carrinho[medicamentoId] = { nome: item.nome, preco: item.preco, quantidade: 1 };
    }
    renderCarrinho();
}

function alterarQuantidadeCarrinho(medicamentoId, delta) {
    if (!carrinho[medicamentoId]) return;
    carrinho[medicamentoId].quantidade += delta;
    if (carrinho[medicamentoId].quantidade <= 0) {
        delete carrinho[medicamentoId];
    }
    renderCarrinho();
}

function removerDoCarrinho(medicamentoId) {
    delete carrinho[medicamentoId];
    renderCarrinho();
}

function renderCarrinho() {
    const ids = Object.keys(carrinho);
    const areaCarrinho = document.getElementById("carrinho");

    if (!ids.length) {
        areaCarrinho.classList.add("d-none");
        return;
    }
    areaCarrinho.classList.remove("d-none");

    let total = 0;
    document.getElementById("itensCarrinho").innerHTML = ids.map(id => {
        const item = carrinho[id];
        const subtotal = item.preco * item.quantidade;
        total += subtotal;
        return `
            <div class="d-flex justify-content-between align-items-center py-1">
                <span class="small">${item.nome}</span>
                <div class="d-flex align-items-center gap-2">
                    <button class="btn btn-outline-secondary btn-sm py-0 px-2" onclick="alterarQuantidadeCarrinho(${id}, -1)">−</button>
                    <span class="small">${item.quantidade}</span>
                    <button class="btn btn-outline-secondary btn-sm py-0 px-2" onclick="alterarQuantidadeCarrinho(${id}, 1)">+</button>
                    <span class="small fw-semibold" style="min-width:80px; text-align:right;">${subtotal.toLocaleString("pt-CV")} CVE</span>
                    <button class="btn btn-outline-danger btn-sm py-0 px-2" onclick="removerDoCarrinho(${id})">🗑️</button>
                </div>
            </div>
        `;
    }).join("");

    document.getElementById("totalCarrinho").innerText = `${total.toLocaleString("pt-CV")} CVE`;
}

async function enviarPedido() {
    const ids = Object.keys(carrinho);
    if (!ids.length) {
        mostrarMensagem("O carrinho está vazio.", "warning");
        return;
    }

    const itens = ids.map(id => ({
        medicamento_id: parseInt(id),
        quantidade: carrinho[id].quantidade
    }));

    const morada = document.getElementById("moradaEntrega").value.trim();
    if (!morada) {
        mostrarMensagem("Indica a morada de entrega antes de enviar o pedido.", "warning");
        return;
    }

    // Pagamento: validado aqui no browser. Ao servidor só vão o método e os
    // últimos 4 dígitos — o número completo e o CVV nunca saem desta função.
    const pag = validarCartao();
    if (!pag.ok) { mostrarMensagem(pag.erro, "warning"); return; }

    const res = await fetch(`${API_URL}/pedidos`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
        body: JSON.stringify({
            itens,
            morada_entrega: morada,
            entrega_lat: entregaCoords ? entregaCoords.lat : null,
            entrega_lng: entregaCoords ? entregaCoords.lng : null,
            metodo_pagamento: pag.metodo,
            cartao_ultimos4: pag.ultimos4
        })
    });

    const data = await res.json();

    if (res.ok) {
        mostrarMensagem("✅ Pagamento aceite. Pedido enviado! A farmácia vai confirmar em breve.");
        carrinho = {};
        entregaCoords = null;
        document.getElementById("moradaEntrega").value = "";
        document.getElementById("coordEntrega").textContent = "Nenhum ponto marcado no mapa.";
        ["cardNome", "cardNumero", "cardValidade", "cardCVV"].forEach(id => {
            const el = document.getElementById(id); if (el) el.value = "";
        });
        renderCarrinho();
        document.getElementById("areaNovoPedido").classList.remove("show");
        carregarMeusPedidos();
    } else {
        mostrarMensagem(data.detail || "Erro ao enviar o pedido.", "danger");
    }
}

// Valida os dados do cartao no browser. Devolve apenas o metodo e os ultimos 4
// digitos. O numero completo e o CVV NUNCA saem desta funcao.
function validarCartao() {
    const metodoEl = document.querySelector('input[name="metodoPag"]:checked');
    const metodo = metodoEl ? metodoEl.value : null;
    if (!metodo) return { ok: false, erro: "Escolhe o método de pagamento." };

    const nome = (document.getElementById("cardNome").value || "").trim();
    const numero = (document.getElementById("cardNumero").value || "").replace(/\s+/g, "");
    const validade = (document.getElementById("cardValidade").value || "").trim();
    const cvv = (document.getElementById("cardCVV").value || "").trim();

    if (nome.length < 2) return { ok: false, erro: "Indica o nome no cartão." };
    if (!/^\d{13,19}$/.test(numero) || !luhnValido(numero))
        return { ok: false, erro: "Número de cartão inválido." };
    const m = validade.match(/^(\d{2})\/(\d{2})$/);
    if (!m) return { ok: false, erro: "Validade inválida (usa o formato MM/AA)." };
    const mes = parseInt(m[1], 10), ano = 2000 + parseInt(m[2], 10);
    if (mes < 1 || mes > 12) return { ok: false, erro: "Mês de validade inválido." };
    const fimMes = new Date(ano, mes, 0, 23, 59, 59);
    if (fimMes < new Date()) return { ok: false, erro: "O cartão está expirado." };
    if (!/^\d{3,4}$/.test(cvv)) return { ok: false, erro: "CVV inválido." };

    return { ok: true, metodo, ultimos4: numero.slice(-4) };
}

// Algoritmo de Luhn — a mesma verificacao que os sistemas reais usam para
// detetar numeros de cartao invalidos antes de tentar cobrar.
function luhnValido(num) {
    let soma = 0, alternar = false;
    for (let i = num.length - 1; i >= 0; i--) {
        let d = parseInt(num[i], 10);
        if (alternar) { d *= 2; if (d > 9) d -= 9; }
        soma += d;
        alternar = !alternar;
    }
    return soma % 10 === 0;
}

/* ── OS MEUS PEDIDOS ─────────────────────────────────────────────────── */
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

async function carregarMeusPedidos() {
    const res = await fetch(`${API_URL}/meus-pedidos`, {
        headers: { "Authorization": "Bearer " + token }
    });
    if (!res.ok) return;

    const pedidos = await res.json();

    if (!pedidos.length) {
        document.getElementById("semPedidos").classList.remove("d-none");
        return;
    }

    document.getElementById("areaPedidos").classList.remove("d-none");
    window._meusPedidos = {};
    pedidos.forEach(p => { window._meusPedidos[p.id] = p; });
    const meuNome = localStorage.getItem("nome") || "Cliente";
    document.getElementById("tabelaPedidos").innerHTML = pedidos.map(p => {
        const itensTexto = p.itens.map(i => `${i.quantidade}× ${i.medicamento_nome}`).join(", ");
        const podeCancelar = p.estado === "pendente";
        return `
            <tr>
                <td class="text-muted small">#${p.id}</td>
                <td class="small">${p.criado_em ? p.criado_em.substring(0, 16).replace("T", " ") : "—"}</td>
                <td class="small">${itensTexto}</td>
                <td class="fw-bold">${parseFloat(p.total).toLocaleString("pt-CV")} CVE</td>
                <td><span class="badge bg-${ESTADO_BADGE[p.estado] || "secondary"}">${ESTADO_TEXTO[p.estado] || p.estado}</span></td>
                <td>
                    <button class="btn btn-outline-secondary btn-sm" onclick="imprimirTalaoPedido(window._meusPedidos[${p.id}], '${meuNome.replace(/'/g, "")}')" title="Imprimir talão">🖨️</button>
                    ${podeCancelar ? `<button class="btn btn-outline-danger btn-sm ms-1" onclick="cancelarPedido(${p.id})">Cancelar</button>` : ""}
                </td>
            </tr>
        `;
    }).join("");
}

async function cancelarPedido(pedidoId) {
    const ok = await confirmarAcao(
        "Cancelar pedido?",
        "Tens a certeza que queres cancelar este pedido?",
        { tipo: "perigo", textoOk: "Cancelar Pedido", icone: "🛑" }
    );
    if (!ok) return;

    const res = await fetch(`${API_URL}/meus-pedidos/${pedidoId}/cancelar`, {
        method: "POST",
        headers: { "Authorization": "Bearer " + token }
    });
    const data = await res.json();

    if (res.ok) {
        mostrarMensagem("Pedido cancelado.");
        carregarMeusPedidos();
    } else {
        mostrarMensagem(data.detail || "Erro ao cancelar o pedido.", "danger");
    }
}

if (token) carregarConta();