from .db import get_connection


def inserir_fornecedor(nome, nif, telefone, email, endereco, latitude=None, longitude=None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO fornecedores (nome, nif, telefone, email, endereco, latitude, longitude) VALUES (?,?,?,?,?,?,?)",
        (nome, nif, telefone, email, endereco, latitude, longitude)
    )
    conn.commit()
    conn.close()
    
    
def listar_fornecedores():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM fornecedores ORDER BY nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obter_fornecedor_por_id(id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM fornecedores WHERE id = ?", (id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def atualizar_fornecedor(id, nome, nif, telefone, email, endereco, latitude=None, longitude=None):
    conn = get_connection()
    conn.execute(
        "UPDATE fornecedores SET nome=?, nif=?, telefone=?, email=?, endereco=?, latitude=?, longitude=? WHERE id=?",
        (nome, nif, telefone, email, endereco, latitude, longitude, id)
    )
    conn.commit()
    conn.close()
    
    
def deletar_fornecedor(id):
    conn = get_connection()
    conn.execute("DELETE FROM fornecedores WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    
def fornecedor_tem_lotes(id):
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM lotes WHERE fornecedor_id = ?", (id,)
    ).fetchone()[0]
    conn.close()
    return count > 0