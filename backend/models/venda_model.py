from .db import get_connection
from .pontos_model import calcular_pontos_ganhos, calcular_desconto

def criar_venda(cliente: str, itens: list, criado_por: str, cliente_id=None,
                pagamentos: list = None, valor_recebido=None, troco: float = 0,
                pontos_resgatados: int = 0):
    conn = get_connection()
    try:
        total_bruto = round(sum(i["subtotal"] for i in itens), 2)

        # Medicamentos que exigem receita medica tem de vir com o numero da
        # receita preenchido -- validado aqui, nao so no frontend, porque o
        # frontend pode ser contornado.
        for item in itens:
            med = conn.execute(
                "SELECT nome, requer_receita FROM medicamentos WHERE id = ?",
                (item["medicamento_id"],)
            ).fetchone()
            if med and med["requer_receita"] and not (item.get("receita_numero") or "").strip():
                raise ValueError(
                    f"'{med['nome']}' exige receita médica — preencha o número da receita"
                )

        # Agregar quantidades por medicamento (o mesmo med pode vir em
        # várias linhas) e decrementar o stock de forma atómica: o UPDATE
        # só passa se ainda houver stock suficiente. Assim evita-se vender
        # a mais em pedidos concorrentes e o stock nunca fica negativo.
        qtd_por_med = {}
        for item in itens:
            qtd_por_med[item["medicamento_id"]] = (
                qtd_por_med.get(item["medicamento_id"], 0) + item["quantidade"]
            )

        for med_id, qtd in qtd_por_med.items():
            cur = conn.execute(
                "UPDATE medicamentos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                (qtd, med_id, qtd)
            )
            if cur.rowcount == 0:
                conn.rollback()
                raise ValueError(f"Stock insuficiente para o medicamento id={med_id}")

        # Resgate de pontos de fidelidade -- desconta do total antes de
        # validar o pagamento. Verificado aqui (dentro da transação) mesmo
        # que o endpoint já tenha verificado antes, para nunca deixar o
        # saldo ficar negativo por uma corrida concorrente.
        desconto_pontos = 0.0
        if cliente_id and pontos_resgatados > 0:
            cliente_row = conn.execute(
                "SELECT pontos_fidelidade FROM clientes WHERE id = ?", (cliente_id,)
            ).fetchone()
            saldo_atual = cliente_row["pontos_fidelidade"] if cliente_row else 0
            if pontos_resgatados > saldo_atual:
                raise ValueError(
                    f"Saldo de pontos insuficiente (tem {saldo_atual}, tentou usar {pontos_resgatados})"
                )
            desconto_pontos = calcular_desconto(pontos_resgatados)

        total = round(total_bruto - desconto_pontos, 2)
        pontos_ganhos = calcular_pontos_ganhos(total) if cliente_id else 0

        if valor_recebido is None:
            valor_recebido = total

        cursor = conn.execute(
            """INSERT INTO vendas
               (cliente, cliente_id, total, valor_recebido, troco, criado_por,
                pontos_ganhos, pontos_resgatados, desconto_pontos)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cliente, cliente_id, total, round(valor_recebido, 2), round(troco, 2), criado_por,
             pontos_ganhos, pontos_resgatados, desconto_pontos)
        )
        venda_id = cursor.lastrowid

        for item in itens:
            conn.execute(
                """INSERT INTO venda_itens
                   (venda_id, medicamento_id, medicamento_nome, quantidade, preco_unitario, subtotal, receita_numero, receita_medico)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (venda_id, item["medicamento_id"], item["medicamento_nome"],
                 item["quantidade"], item["preco_unitario"], item["subtotal"],
                 item.get("receita_numero"), item.get("receita_medico"))
            )

        if pagamentos:
            for p in pagamentos:
                conn.execute(
                    "INSERT INTO venda_pagamentos (venda_id, metodo, valor) VALUES (?, ?, ?)",
                    (venda_id, p["metodo"], p["valor"])
                )

        if cliente_id:
            if pontos_resgatados > 0:
                conn.execute(
                    "UPDATE clientes SET pontos_fidelidade = pontos_fidelidade - ? WHERE id = ?",
                    (pontos_resgatados, cliente_id)
                )
                conn.execute(
                    "INSERT INTO pontos_historico (cliente_id, tipo, pontos, motivo, venda_id) VALUES (?,?,?,?,?)",
                    (cliente_id, "resgate", -pontos_resgatados, "Resgate de pontos em compra", venda_id)
                )
            if pontos_ganhos > 0:
                conn.execute(
                    "UPDATE clientes SET pontos_fidelidade = pontos_fidelidade + ? WHERE id = ?",
                    (pontos_ganhos, cliente_id)
                )
                conn.execute(
                    "INSERT INTO pontos_historico (cliente_id, tipo, pontos, motivo, venda_id) VALUES (?,?,?,?,?)",
                    (cliente_id, "ganho", pontos_ganhos, "Pontos ganhos em compra", venda_id)
                )

        conn.commit()
        return venda_id
    finally:
        conn.close()

def listar_vendas():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM vendas ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def obter_venda(id: int):
    conn = get_connection()
    venda = conn.execute("SELECT * FROM vendas WHERE id = ?", (id,)).fetchone()
    if not venda:
        conn.close()
        return None
    itens = conn.execute(
        "SELECT * FROM venda_itens WHERE venda_id = ?", (id,)
    ).fetchall()
    pagamentos = conn.execute(
        "SELECT * FROM venda_pagamentos WHERE venda_id = ?", (id,)
    ).fetchall()
    devolucoes = conn.execute(
        "SELECT * FROM devolucoes WHERE venda_id = ? ORDER BY id", (id,)
    ).fetchall()
    conn.close()
    result = dict(venda)
    result["itens"] = [dict(i) for i in itens]
    result["pagamentos"] = [dict(p) for p in pagamentos]
    result["devolucoes"] = [dict(d) for d in devolucoes]
    result["total_devolvido"] = round(sum(d["valor"] for d in result["devolucoes"]), 2)

    # quanto ja foi devolvido de cada medicamento
    dev_por_med = {}
    for d in result["devolucoes"]:
        dev_por_med[d["medicamento_id"]] = dev_por_med.get(d["medicamento_id"], 0) + d["quantidade"]
    for i in result["itens"]:
        i["qtd_devolvida"] = dev_por_med.get(i["medicamento_id"], 0)

    return result

def criar_devolucao(venda_id: int, medicamento_id: int, quantidade: int,
                    criado_por: str, motivo: str = None):
    """Devolve `quantidade` unidades de um item de uma venda: repoe o stock e
    regista a devolucao. Nao se pode devolver mais do que foi vendido (menos o
    que ja foi devolvido), nem de uma venda anulada."""
    if quantidade is None or quantidade <= 0:
        raise ValueError("A quantidade a devolver tem de ser positiva")

    conn = get_connection()
    try:
        venda = conn.execute("SELECT * FROM vendas WHERE id = ?", (venda_id,)).fetchone()
        if not venda:
            return None
        if venda["anulada"]:
            raise ValueError("Não é possível devolver itens de uma venda anulada")

        item = conn.execute(
            "SELECT * FROM venda_itens WHERE venda_id = ? AND medicamento_id = ?",
            (venda_id, medicamento_id)
        ).fetchone()
        if not item:
            raise ValueError("Esse medicamento não faz parte desta venda")

        ja_devolvido = conn.execute(
            "SELECT COALESCE(SUM(quantidade), 0) FROM devolucoes WHERE venda_id = ? AND medicamento_id = ?",
            (venda_id, medicamento_id)
        ).fetchone()[0]

        disponivel = item["quantidade"] - ja_devolvido
        if quantidade > disponivel:
            raise ValueError(f"Só podes devolver até {disponivel} unidade(s) deste item")

        valor = round(item["preco_unitario"] * quantidade, 2)

        # repor o stock do medicamento (se ainda existir)
        conn.execute(
            "UPDATE medicamentos SET estoque = estoque + ? WHERE id = ?",
            (quantidade, medicamento_id)
        )
        conn.execute(
            """INSERT INTO devolucoes
               (venda_id, medicamento_id, medicamento_nome, quantidade, valor, motivo, criado_por)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (venda_id, medicamento_id, item["medicamento_nome"], quantidade, valor, motivo, criado_por)
        )
        conn.commit()
        return {"valor": valor, "medicamento_nome": item["medicamento_nome"], "quantidade": quantidade}
    finally:
        conn.close()

def anular_venda(venda_id: int, anulada_por: str, motivo: str = None):
    """Anula uma venda: repõe o stock dos itens e marca a venda como anulada.
    Não apaga o registo (mantém histórico/auditoria). Idempotente: anular
    uma venda já anulada levanta ValueError."""
    conn = get_connection()
    try:
        venda = conn.execute("SELECT * FROM vendas WHERE id = ?", (venda_id,)).fetchone()
        if not venda:
            return None
        if venda["anulada"]:
            raise ValueError("Esta venda já estava anulada")
 
        itens = conn.execute(
            "SELECT medicamento_id, quantidade FROM venda_itens WHERE venda_id = ?",
            (venda_id,)
        ).fetchall()
        for it in itens:
            # Repor apenas o que ainda estava "fora": a quantidade vendida menos
            # o que ja tinha sido devolvido (para nao repor stock em duplicado).
            ja_devolvido = conn.execute(
                "SELECT COALESCE(SUM(quantidade), 0) FROM devolucoes WHERE venda_id = ? AND medicamento_id = ?",
                (venda_id, it["medicamento_id"])
            ).fetchone()[0]
            repor = it["quantidade"] - ja_devolvido
            if repor > 0:
                conn.execute(
                    "UPDATE medicamentos SET estoque = estoque + ? WHERE id = ?",
                    (repor, it["medicamento_id"])
                )

        if venda["cliente_id"]:
            if venda["pontos_ganhos"] > 0:
                # nunca deixar o saldo ficar negativo, mesmo que o cliente
                # entretanto ja tenha gasto esses pontos noutra compra
                conn.execute(
                    "UPDATE clientes SET pontos_fidelidade = MAX(0, pontos_fidelidade - ?) WHERE id = ?",
                    (venda["pontos_ganhos"], venda["cliente_id"])
                )
                conn.execute(
                    "INSERT INTO pontos_historico (cliente_id, tipo, pontos, motivo, venda_id) VALUES (?,?,?,?,?)",
                    (venda["cliente_id"], "ajuste", -venda["pontos_ganhos"], "Reversão por anulação de venda", venda_id)
                )
            if venda["pontos_resgatados"] > 0:
                conn.execute(
                    "UPDATE clientes SET pontos_fidelidade = pontos_fidelidade + ? WHERE id = ?",
                    (venda["pontos_resgatados"], venda["cliente_id"])
                )
                conn.execute(
                    "INSERT INTO pontos_historico (cliente_id, tipo, pontos, motivo, venda_id) VALUES (?,?,?,?,?)",
                    (venda["cliente_id"], "ajuste", venda["pontos_resgatados"], "Reposição por anulação de venda", venda_id)
                )
 
        conn.execute(
            """UPDATE vendas
               SET anulada = 1, anulada_em = datetime('now'),
                   anulada_por = ?, motivo_anulacao = ?
               WHERE id = ?""",
            (anulada_por, motivo, venda_id)
        )
        conn.commit()
        return True
    finally:
        conn.close()
 
def resumo_vendas():
    conn = get_connection()
    total = conn.execute("SELECT COALESCE(SUM(total), 0) FROM vendas").fetchone()[0]
    count = conn.execute("SELECT COUNT(*) FROM vendas").fetchone()[0]
    hoje  = conn.execute(
        "SELECT COALESCE(SUM(total), 0) FROM vendas WHERE DATE(criado_em) = DATE('now')"
    ).fetchone()[0]
    mensais = conn.execute("""
        SELECT strftime('%m', criado_em) as mes, COALESCE(SUM(total), 0) as total
        FROM vendas
        WHERE strftime('%Y', criado_em) = strftime('%Y', 'now')
        GROUP BY mes ORDER BY mes
    """).fetchall()
    conn.close()

    # Receita liquida = vendas nao anuladas - devolucoes (nao altera total_geral,
    # para nao afetar quem ja depende desse campo).
    conn2 = get_connection()
    total_validas = conn2.execute(
        "SELECT COALESCE(SUM(total), 0) FROM vendas WHERE anulada = 0"
    ).fetchone()[0]
    total_devolvido = conn2.execute(
        """SELECT COALESCE(SUM(d.valor), 0)
           FROM devolucoes d JOIN vendas v ON v.id = d.venda_id
           WHERE v.anulada = 0"""
    ).fetchone()[0]
    conn2.close()

    return {
        "total_geral": round(total, 2),
        "total_vendas": count,
        "vendas_hoje": round(hoje, 2),
        "total_devolvido": round(total_devolvido, 2),
        "receita_liquida": round(total_validas - total_devolvido, 2),
        "mensais": [dict(r) for r in mensais]
    }

def vendas_por_periodo(inicio: str, fim: str):
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM vendas
           WHERE DATE(criado_em) BETWEEN DATE(?) AND DATE(?)
           ORDER BY criado_em DESC""",
        (inicio, fim)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def top_produtos(inicio: str = None, fim: str = None, limite: int = 5):
    conn = get_connection()
    if inicio and fim:
        rows = conn.execute(
            """SELECT vi.medicamento_nome,
                      SUM(vi.quantidade) as total_qtd,
                      SUM(vi.subtotal) as total_valor
               FROM venda_itens vi
               JOIN vendas v ON v.id = vi.venda_id
               WHERE DATE(v.criado_em) BETWEEN DATE(?) AND DATE(?)
               GROUP BY vi.medicamento_nome
               ORDER BY total_qtd DESC
               LIMIT ?""",
            (inicio, fim, limite)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT medicamento_nome,
                      SUM(quantidade) as total_qtd,
                      SUM(subtotal) as total_valor
               FROM venda_itens
               GROUP BY medicamento_nome
               ORDER BY total_qtd DESC
               LIMIT ?""",
            (limite,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def resumo_pagamentos(inicio: str = None, fim: str = None):
    conn = get_connection()
    if inicio and fim:
        rows = conn.execute(
            """SELECT vp.metodo, SUM(vp.valor) as total
               FROM venda_pagamentos vp
               JOIN vendas v ON v.id = vp.venda_id
               WHERE DATE(v.criado_em) BETWEEN DATE(?) AND DATE(?)
               GROUP BY vp.metodo
               ORDER BY total DESC""",
            (inicio, fim)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT metodo, SUM(valor) as total
               FROM venda_pagamentos
               GROUP BY metodo
               ORDER BY total DESC"""
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def relatorio_margem(inicio: str = None, fim: str = None):
    """Agrega receita, custo e lucro por medicamento vendido, usando o
    preco_custo ATUAL do medicamento (não fica guardado por venda, por isso
    se o custo mudar depois de uma venda antiga, o relatório reflete o custo
    de hoje, não o de quando a venda foi feita — é uma aproximação razoável
    para uma farmácia pequena, mas vale a pena saber desta limitação).
    Vendas anuladas são sempre excluídas."""
    conn = get_connection()
    filtro_periodo = ""
    params = []
    if inicio and fim:
        filtro_periodo = "AND DATE(v.criado_em) BETWEEN DATE(?) AND DATE(?)"
        params = [inicio, fim]

    rows = conn.execute(
        f"""SELECT
                vi.medicamento_nome,
                SUM(vi.quantidade) as quantidade_vendida,
                SUM(vi.subtotal) as receita,
                SUM(vi.quantidade * COALESCE(m.preco_custo, 0)) as custo,
                SUM(CASE WHEN m.preco_custo IS NULL THEN vi.quantidade ELSE 0 END) as unidades_sem_custo
           FROM venda_itens vi
           JOIN vendas v ON v.id = vi.venda_id
           LEFT JOIN medicamentos m ON m.id = vi.medicamento_id
           WHERE v.anulada = 0 {filtro_periodo}
           GROUP BY vi.medicamento_nome
           ORDER BY (SUM(vi.subtotal) - SUM(vi.quantidade * COALESCE(m.preco_custo, 0))) DESC""",
        params
    ).fetchall()
    conn.close()

    produtos = []
    total_receita = 0.0
    total_custo = 0.0
    total_unidades_sem_custo = 0

    for r in rows:
        receita = round(r["receita"], 2)
        custo = round(r["custo"], 2)
        lucro = round(receita - custo, 2)
        margem_pct = round((lucro / receita) * 100, 1) if receita > 0 else 0.0

        produtos.append({
            "medicamento_nome": r["medicamento_nome"],
            "quantidade_vendida": r["quantidade_vendida"],
            "receita": receita,
            "custo": custo,
            "lucro": lucro,
            "margem_pct": margem_pct,
            "unidades_sem_custo": r["unidades_sem_custo"]
        })
        total_receita += receita
        total_custo += custo
        total_unidades_sem_custo += r["unidades_sem_custo"]

    total_lucro = round(total_receita - total_custo, 2)
    margem_pct_geral = round((total_lucro / total_receita) * 100, 1) if total_receita > 0 else 0.0

    return {
        "resumo": {
            "receita_total": round(total_receita, 2),
            "custo_total": round(total_custo, 2),
            "lucro_total": total_lucro,
            "margem_pct": margem_pct_geral,
            "unidades_sem_custo_definido": total_unidades_sem_custo
        },
        "produtos": produtos
    }


def auditoria_receitas(inicio: str = None, fim: str = None):
    """Lista todas as vendas de medicamentos que exigem receita médica,
    com o número da receita e o médico prescritor registados -- para
    fins de conformidade/auditoria."""
    conn = get_connection()
    filtro_periodo = ""
    params = []
    if inicio and fim:
        filtro_periodo = "AND DATE(v.criado_em) BETWEEN DATE(?) AND DATE(?)"
        params = [inicio, fim]

    rows = conn.execute(
        f"""SELECT
                vi.id as item_id, vi.venda_id, vi.medicamento_nome, vi.quantidade,
                vi.receita_numero, vi.receita_medico,
                v.cliente, v.criado_em, v.criado_por, v.anulada
           FROM venda_itens vi
           JOIN vendas v ON v.id = vi.venda_id
           JOIN medicamentos m ON m.id = vi.medicamento_id
           WHERE m.requer_receita = 1 {filtro_periodo}
           ORDER BY v.criado_em DESC""",
        params
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def vendas_por_utilizador(inicio: str = None, fim: str = None):
    conn = get_connection()
    if inicio and fim:
        rows = conn.execute(
            """SELECT criado_por,
                      COUNT(*) as n_vendas,
                      SUM(total) as total_valor
               FROM vendas
               WHERE DATE(criado_em) BETWEEN DATE(?) AND DATE(?)
               GROUP BY criado_por
               ORDER BY total_valor DESC""",
            (inicio, fim)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT criado_por,
                      COUNT(*) as n_vendas,
                      SUM(total) as total_valor
               FROM vendas
               GROUP BY criado_por
               ORDER BY total_valor DESC"""
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]