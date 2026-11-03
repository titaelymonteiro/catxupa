from .db import get_connection
 
def criar_lote(medicamento_id, fornecedor_id, numero_lote, quantidade, validade, preco_custo, criado_por):
    """Regista um lote recebido e aumenta o stock do medicamento correspondente
    (receber um lote é, na prática, uma entrada de stock)."""
    conn = get_connection()
    medicamento = conn.execute(
        "SELECT id FROM medicamentos WHERE id = ?", (medicamento_id,)
    ).fetchone()
    if not medicamento:
        conn.close()
        raise ValueError("Medicamento não encontrado")
        
    if fornecedor_id is not None:
        fornecedor = conn.execute(
            "SELECT id FROM fornecedores WHERE id = ?", (fornecedor_id,)
        ).fetchone()
        if not fornecedor:
            conn.close()
            raise ValueError("Fornecedor não encontrado")
            
            
    cursor = conn.execute(
        """INSERT INTO lotes (medicamento_id, fornecedor_id, numero_lote, quantidade, validade, preco_custo, criado_por)
           VALUES (?,?,?,?,?,?,?)""",
           (medicamento_id, fornecedor_id, numero_lote, quantidade, validade, preco_custo, criado_por)
    )
    lote_id = cursor.lastrowid
    
    conn.execute(
        "UPDATE medicamentos SET estoque = estoque + ? WHERE id = ?",
        (quantidade, medicamento_id)
    )
    
    conn.commit()
    conn.close()
    return lote_id

def listar_lotes():
    conn = get_connection()
    rows = conn.execute("""
        SELECT lotes.*, medicamentos.nome AS medicamento_nome, fornecedores.nome AS fornecedor_nome
        FROM lotes
        JOIN medicamentos ON medicamentos.id = lotes.medicamento_id
        LEFT JOIN fornecedores ON fornecedores.id = lotes.fornecedor_id
        ORDER BY lotes.validade ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def listar_lotes_por_medicamento(medicamento_id):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT lotes.*, fornecedores.nome AS fornecedor_nome
        FROM lotes
        LEFT JOIN fornecedores ON fornecedores.id = lotes.fornecedor_id
        WHERE medicamento_id = ?
        ORDER BY lotes.validade ASC
    """, (medicamento_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obter_lote_por_id(id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM lotes WHERE id = ?", (id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def deletar_lote(id):
    """Remove o lote e desconta a quantidade correspondente do stock
    (nunca deixa o stock ficar negativo)."""
    conn = get_connection()
    lote = conn.execute("SELECT * FROM lotes WHERE id = ?", (id,)).fetchone()
    if not lote:
        conn.close()
        raise ValueError("Lote não encontrado")
        
    conn.execute(
        "UPDATE medicamentos SET estoque = MAX(0, estoque - ?) WHERE id = ?",
        (lote["quantidade"], lote["medicamento_id"])
    )
    conn.execute("DELETE FROM lotes WHERE id = ?", (id,))
    conn.commit()
    conn.close()