from .db import get_connection

def registrar_log(usuario: str, acao: str, detalhes: str = None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO auditoria (usuario, acao, detalhes) VALUES (?, ?, ?)",
        (usuario, acao, detalhes)
    )
    conn.commit()
    conn.close()

def listar_logs():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM auditoria ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
