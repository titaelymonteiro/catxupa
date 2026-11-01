// talao.js — Talao/recibo imprimivel de um pedido online.
// Partilhado pelo staff (pedidos.js) e pelo cliente (portal.js).

const _ESTADO_TALAO = {
    pendente: "Pendente", confirmado: "Confirmado", pronto: "Pronto",
    concluido: "Concluido", cancelado: "Cancelado"
};

function imprimirTalaoPedido(p, nomeCliente) {
    if (!p) return;
    const fmt = (n) => parseFloat(n || 0).toLocaleString("pt-CV") + " CVE";
    const cliente = p.cliente_nome || nomeCliente || "Cliente";
    const data = p.criado_em ? p.criado_em.substring(0, 16).replace("T", " ") : "—";
    const estado = _ESTADO_TALAO[p.estado] || p.estado || "";

    const itens = (p.itens || []).map(i => `
        <tr>
            <td>${i.medicamento_nome}</td>
            <td class="c">${i.quantidade}</td>
            <td class="r">${fmt(i.preco_unitario)}</td>
            <td class="r">${fmt(i.subtotal)}</td>
        </tr>`).join("");

    const entrega = p.morada_entrega
        ? `<div class="linha"></div><div class="bloco"><strong>Entrega:</strong><br>${p.morada_entrega}</div>`
        : "";
    const nota = p.nota ? `<div class="bloco"><strong>Nota:</strong> ${p.nota}</div>` : "";
    const anulado = (p.estado === "cancelado")
        ? '<div class="anulado">*** PEDIDO CANCELADO ***</div>' : "";

    const html = `<!DOCTYPE html><html lang="pt"><head><meta charset="utf-8">
        <title>Talao Pedido #${p.id}</title>
        <style>
            *{box-sizing:border-box;}
            body{font-family:'Courier New',monospace;color:#000;margin:0;padding:12px;}
            .recibo{width:300px;margin:0 auto;}
            h1{font-size:18px;text-align:center;margin:0;letter-spacing:1px;}
            .sub{text-align:center;font-size:11px;margin:2px 0 8px;}
            .linha{border-top:1px dashed #000;margin:8px 0;}
            .meta{font-size:12px;}
            .meta div{display:flex;justify-content:space-between;}
            table{width:100%;border-collapse:collapse;font-size:11px;margin-top:4px;}
            th{text-align:left;border-bottom:1px solid #000;padding:2px 0;}
            td{padding:2px 0;vertical-align:top;}
            .c{text-align:center;} .r{text-align:right;}
            .total{display:flex;justify-content:space-between;font-size:15px;font-weight:bold;margin-top:6px;}
            .bloco{font-size:12px;margin-top:8px;}
            .obrigado{text-align:center;font-size:11px;margin-top:10px;}
            .anulado{text-align:center;color:#b00;font-weight:bold;font-size:13px;margin:8px 0;}
            @media print{body{padding:0;}}
        </style></head><body>
        <div class="recibo">
            <h1>FARMACIA CV</h1>
            <div class="sub">Talao de Encomenda Online</div>
            ${anulado}
            <div class="linha"></div>
            <div class="meta">
                <div><span>Pedido:</span><span>#${p.id}</span></div>
                <div><span>Data:</span><span>${data}</span></div>
                <div><span>Cliente:</span><span>${cliente}</span></div>
                <div><span>Estado:</span><span>${estado}</span></div>
            </div>
            <div class="linha"></div>
            <table>
                <thead><tr><th>Produto</th><th class="c">Qtd</th><th class="r">Preco</th><th class="r">Subtotal</th></tr></thead>
                <tbody>${itens}</tbody>
            </table>
            <div class="linha"></div>
            <div class="total"><span>TOTAL</span><span>${fmt(p.total)}</span></div>
            ${entrega}
            ${nota}
            <div class="linha"></div>
            <div class="obrigado">Obrigado pela preferencia!</div>
        </div>
        <script>window.onload=function(){window.print();}<\/script>
        </body></html>`;

    const win = window.open("", "_blank", "width=380,height=680");
    if (!win) { alert("O navegador bloqueou a janela. Permite pop-ups para imprimir o talao."); return; }
    win.document.open();
    win.document.write(html);
    win.document.close();
}