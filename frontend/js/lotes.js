const token = localStorage.getItem("token");
if (!token) { window.location.href = "login.html"; }

let lotesTodos = [];
let paginaAtual = 1;
const ITENS_POR_PAGINA = 8;

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
            <td><div class="skeleton-bar" style="width:80px;"></div></td>
            <td><div class="skeleton-bar" style="width:60px;"></div></td>
            <td><div class="skeleton-bar" style="width:90px;"></div></td>
            <td><div class="skeleton-bar" style="width:80px;"></div></td>
            <td><div class="skeleton-bar" style="width:120px;"></div></td>
            <td><div class="skeleton-bar" style="width:100px;"></div></td>
            <td><div class="skeleton-bar" style="width:70px;"></div></td>
        </tr>`;
    }
    document.getElementById("tabela").innerHTML = html;
}

async function carregarSelects() {
    const [resMeds, resForn] = await Promise.all([
        fetch(`${API_URL}/medicamentos`, { headers: { "Authorization": "Bearer " + token } }),
        fetch(`${API_URL}/fornecedores`, { headers: { "Authorization": "Bearer " + token } })
    ]);
    const meds = await resMeds.json();
    const forns = await resForn.json();

    const selMed = document.getElementById("medicamentoId");
    meds.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m.id;
        opt.textContent = m.nome;
        selMed.appendChild(opt);
    });

    const selForn = document.getElementById("fornecedorId");
    forns.forEach(f => {
        const opt = document.createElement("option");
        opt.value = f.id;
        opt.textContent = f.nome;
        selForn.appendChild(opt);
    });
}

function diasEStiloValidade(validade) {
    const hoje = new Date();
    const dataValidade = new Date(validade + "T00:00:00");
    const dias = Math.ceil((dataValidade - hoje) / (1000 * 60 * 60 * 24));
    if (dias < 0) return { texto: `${validade} ⛔ vencido`, classe: "text-danger fw-bold" };
    if (dias <= 30) return { texto: `${validade} ⚠️ ${dias}d`, classe: "text-warning fw-bold" };
    return { texto: validade, classe: "" };
}

async function carregar() {
    renderSkeleton();
    try {
        const res = await fetch(`${API_URL}/lotes`, {
            headers: { "Authorization": "Bearer " + token }
        });
        if (res.status === 401) { window.location.href = "login.html"; return; }

        lotesTodos = await res.json();
        paginaAtual = 1;
        renderTabela(lotesTodos);

    } catch (err) {
        console.error(err);
        mostrarMensagem("Erro de ligação com o servidor.", "danger");
    }
}

function renderTabela(lista) {
    if (!lista.length) {
        document.getElementById("tabela").innerHTML =
            "<tr><td colspan='9' class='text-center text-muted py-4'>Nenhum lote registado ainda.</td></tr>";
        document.getElementById("paginacaoBar").style.display = "none";
        return;
    }

    const { paginaAtual: pag, totalPaginas, itens } = fatiarPagina(lista, paginaAtual, ITENS_POR_PAGINA);
    paginaAtual = pag;

    document.getElementById("tabela").innerHTML = itens.map(l => {
        const v = diasEStiloValidade(l.validade);
        return `
        <tr>
            <td class="text-muted small">#${l.id}</td>
            <td class="fw-semibold">${l.medicamento_nome}</td>
            <td>${l.numero_lote}</td>
            <td>${l.quantidade}</td>
            <td class="${v.classe}">${v.texto}</td>
            <td>${l.preco_custo != null ? parseFloat(l.preco_custo).toLocaleString("pt-CV") + " CVE" : "—"}</td>
            <td>${l.fornecedor_nome || "—"}</td>
            <td class="small text-muted">${l.criado_em ? l.criado_em.substring(0, 10) : "—"}</td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="apagar(${l.id})" title="Apagar (desconta do stock)">🗑️</button>
            </td>
        </tr>`;
    }).join("");

    renderPaginacao(lista.length, paginaAtual, totalPaginas, ITENS_POR_PAGINA, "lotes");
}

function irParaPagina(p) {
    paginaAtual = p;
    const termo = document.getElementById("busca").value.toLowerCase();
    const lista = termo
        ? lotesTodos.filter(l =>
            l.medicamento_nome.toLowerCase().includes(termo) ||
            l.numero_lote.toLowerCase().includes(termo) ||
            (l.fornecedor_nome || "").toLowerCase().includes(termo))
        : lotesTodos;
    renderTabela(lista);
}

function filtrar() {
    paginaAtual = 1;
    const termo = document.getElementById("busca").value.toLowerCase();
    const filtrados = lotesTodos.filter(l =>
        l.medicamento_nome.toLowerCase().includes(termo) ||
        l.numero_lote.toLowerCase().includes(termo) ||
        (l.fornecedor_nome || "").toLowerCase().includes(termo)
    );
    renderTabela(filtrados);
}

async function adicionar() {
    const medicamento_id = document.getElementById("medicamentoId").value;
    const fornecedor_id = document.getElementById("fornecedorId").value;
    const numero_lote = document.getElementById("numeroLote").value.trim();
    const quantidade = document.getElementById("quantidade").value;
    const validade = document.getElementById("validade").value;
    const preco_custo = document.getElementById("precoCusto").value;

    if (!medicamento_id || !numero_lote || !quantidade || !validade) {
        mostrarMensagem("Preenche medicamento, nº de lote, quantidade e validade.", "warning");
        return;
    }

    const res = await fetch(`${API_URL}/lotes`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
        body: JSON.stringify({
            medicamento_id: parseInt(medicamento_id),
            fornecedor_id: fornecedor_id ? parseInt(fornecedor_id) : null,
            numero_lote,
            quantidade: parseInt(quantidade),
            validade,
            preco_custo: preco_custo ? parseFloat(preco_custo) : null
        })
    });

    if (res.ok) {
        mostrarMensagem("Lote registado e stock atualizado!");
        ["numeroLote", "quantidade", "validade", "precoCusto"].forEach(id => document.getElementById(id).value = "");
        document.getElementById("medicamentoId").value = "";
        document.getElementById("fornecedorId").value = "";
        document.getElementById("formAdicionar").classList.remove("show");
        carregar();
    } else {
        const data = await res.json();
        mostrarMensagem(data.detail || "Erro ao registar lote.", "danger");
    }
}

async function apagar(id) {
    const lote = lotesTodos.find(l => l.id === id);
    const ok = await confirmarAcao(
        "Apagar lote?",
        `Vai descontar ${lote.quantidade} unidades do stock de "${lote.medicamento_nome}". Tens a certeza?`,
        { tipo: "perigo", textoOk: "Apagar", icone: "🗑️" }
    );
    if (!ok) return;

    const res = await fetch(`${API_URL}/lotes/${id}`, {
        method: "DELETE",
        headers: { "Authorization": "Bearer " + token }
    });

    if (res.ok) {
        mostrarMensagem("Lote removido e stock ajustado.");
        carregar();
    } else {
        const data = await res.json();
        mostrarMensagem(data.detail || "Erro ao remover lote.", "danger");
    }
}

if (token) {
    carregarSelects();
    carregar();
}