from .db import get_connection

def inserir_medicamento(nome, preco, estoque, validade, categoria, criado_por=None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO medicamentos (nome, preco, estoque, validade, categoria, criado_por) VALUES (?,?,?,?,?,?)",
        (nome, preco, estoque, validade, categoria, criado_por)
    )
    conn.commit()
    conn.close()

def listar_medicamentos():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM medicamentos ORDER BY nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def obter_medicamento_por_id(id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM medicamentos WHERE id = ?", (id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def atualizar_medicamento(id, nome, preco, estoque, validade, categoria):
    conn = get_connection()
    conn.execute(
        "UPDATE medicamentos SET nome=?, preco=?, estoque=?, validade=?, categoria=? WHERE id=?",
        (nome, preco, estoque, validade, categoria, id)
    )
    conn.commit()
    conn.close()

def deletar_medicamento(id):
    conn = get_connection()
    conn.execute("DELETE FROM medicamentos WHERE id = ?", (id,))
    conn.commit()
    conn.close()

def contar_stock_baixo(limite=10):
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM medicamentos WHERE estoque < ?", (limite,)
    ).fetchone()[0]
    conn.close()
    return count

def contar_vencimento_proximo(dias=30):
    conn = get_connection()
    # SQLite DATE format 'YYYY-MM-DD'
    count = conn.execute(
        "SELECT COUNT(*) FROM medicamentos WHERE validade != '' AND validade <= date('now', '+' || ? || ' days') AND validade >= date('now')",
        (dias,)
    ).fetchone()[0]
    conn.close()
    return count

def listar_vencimento_proximo(dias=30):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM medicamentos WHERE validade != '' AND validade <= date('now', '+' || ? || ' days') AND validade >= date('now') ORDER BY validade ASC",
        (dias,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def ultimos_medicamentos(n=5):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM medicamentos ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
