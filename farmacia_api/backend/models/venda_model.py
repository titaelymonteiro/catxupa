from .db import get_connection
 
def criar_tabelas_vendas():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente     TEXT    NOT NULL DEFAULT 'Cliente Geral',
            total       REAL    NOT NULL,
            criado_em   TEXT    DEFAULT (datetime('now')),
            criado_por  TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS venda_itens (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id        INTEGER NOT NULL,
            medicamento_id  INTEGER NOT NULL,
            medicamento_nome TEXT   NOT NULL,
            quantidade      INTEGER NOT NULL,
            preco_unitario  REAL    NOT NULL,
            subtotal        REAL    NOT NULL,
            FOREIGN KEY (venda_id) REFERENCES vendas(id)
        )
    """)
    conn.commit()
    conn.close()
 
def criar_venda(cliente: str, itens: list, criado_por: str, metodo: str = "Dinheiro", status: str = "Efetuado"):
    conn = get_connection()
    total = sum(i["subtotal"] for i in itens)
    cursor = conn.execute(
        "INSERT INTO vendas (cliente, total, criado_por, metodo_pagamento, status_pagamento) VALUES (?, ?, ?, ?, ?)",
        (cliente, total, criado_por, metodo, status)
    )
    venda_id = cursor.lastrowid
    for item in itens:
        conn.execute(
            """INSERT INTO venda_itens
               (venda_id, medicamento_id, medicamento_nome, quantidade, preco_unitario, subtotal)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (venda_id, item["medicamento_id"], item["medicamento_nome"],
             item["quantidade"], item["preco_unitario"], item["subtotal"])
        )
        # Baixar stock
        conn.execute(
            "UPDATE medicamentos SET estoque = estoque - ? WHERE id = ?",
            (item["quantidade"], item["medicamento_id"])
        )
    conn.commit()
    conn.close()
    return venda_id

def atualizar_venda_pagamento(venda_id: int, status: str, pagali_id: str = None):
    conn = get_connection()
    conn.execute(
        "UPDATE vendas SET status_pagamento = ?, pagali_id = ? WHERE id = ?",
        (status, pagali_id, venda_id)
    )
    conn.commit()
    conn.close()
 
def listar_vendas():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM vendas ORDER BY id DESC"
    ).fetchall()
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
    conn.close()
    result = dict(venda)
    result["itens"] = [dict(i) for i in itens]
    return result
 
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
    return {
        "total_geral": round(total, 2),
        "total_vendas": count,
        "vendas_hoje": round(hoje, 2),
        "mensais": [dict(r) for r in mensais]
    }