from .db import get_connection

def registar_log(usuario_email: str, acao: str, entidade: str, entidade_id, descricao: str):
    """
    acao: 'criar' | 'editar' | 'apagar'
    entidade: 'medicamento' | 'cliente' | 'usuario' | 'venda'
    entidade_id: id do registo afetado (ou '-' se não aplicável, ex: criação)
    """
    conn = get_connection()
    conn.execute(
        """INSERT INTO logs (usuario_email, acao, entidade, entidade_id, descricao)
           VALUES (?, ?, ?, ?, ?)""",
        (usuario_email, acao, entidade, str(entidade_id), descricao)
    )
    conn.commit()
    conn.close()

def listar_logs(limite: int = 100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM logs ORDER BY criado_em DESC LIMIT ?", (limite,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def listar_logs_por_entidade(entidade: str, limite: int = 100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM logs WHERE entidade = ? ORDER BY criado_em DESC LIMIT ?",
        (entidade, limite)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
