from .db import get_connection

def listar_clientes():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM clientes ORDER BY nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def obter_cliente_por_id(id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM clientes WHERE id = ?", (id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def criar_cliente(nome: str, telefone: str, email: str, endereco: str):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO clientes (nome, telefone, email, endereco) VALUES (?, ?, ?, ?)",
        (nome, telefone, email, endereco)
    )
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()
    return novo_id

def atualizar_cliente(id: int, nome: str, telefone: str, email: str, endereco: str):
    conn = get_connection()
    conn.execute(
        "UPDATE clientes SET nome=?, telefone=?, email=?, endereco=? WHERE id=?",
        (nome, telefone, email, endereco, id)
    )
    conn.commit()
    conn.close()

def deletar_cliente(id: int):
    conn = get_connection()
    conn.execute("DELETE FROM clientes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

def contar_clientes():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    conn.close()
    return count

def historico_compras_cliente(cliente_id: int):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM vendas WHERE cliente_id = ? ORDER BY id DESC", (cliente_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
