"""Notificacoes internas para o staff (ex.: novo pedido online).

Guardadas na tabela `notificacoes` (id, tipo, mensagem, link, lida, criado_em).
"""
from .db import get_connection


def criar_notificacao(tipo: str, mensagem: str, link: str = None):
    """Cria uma notificacao. Devolve o id criado."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO notificacoes (tipo, mensagem, link) VALUES (?, ?, ?)",
            (tipo, mensagem, link)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def listar_notificacoes(limite: int = 20):
    """Lista as notificacoes mais recentes primeiro."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, tipo, mensagem, link, lida, criado_em
               FROM notificacoes
               ORDER BY id DESC
               LIMIT ?""",
            (limite,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def contar_nao_lidas() -> int:
    """Numero de notificacoes por ler."""
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM notificacoes WHERE lida = 0"
        ).fetchone()[0]
    finally:
        conn.close()


def marcar_como_lida(notificacao_id: int):
    """Marca uma notificacao como lida."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE notificacoes SET lida = 1 WHERE id = ?", (notificacao_id,)
        )
        conn.commit()
    finally:
        conn.close()


def marcar_todas_como_lidas():
    """Marca todas as notificacoes por ler como lidas."""
    conn = get_connection()
    try:
        conn.execute("UPDATE notificacoes SET lida = 1 WHERE lida = 0")
        conn.commit()
    finally:
        conn.close()


def criar_se_ausente(tipo: str, mensagem: str, link: str = None, chave: str = None):
    """Cria a notificacao apenas se ainda nao existir uma NAO LIDA com a mesma
    `chave`. Evita encher o sino com alertas repetidos (ex.: o mesmo
    medicamento com stock baixo)."""
    conn = get_connection()
    try:
        if chave:
            existe = conn.execute(
                "SELECT 1 FROM notificacoes WHERE chave = ? AND lida = 0 LIMIT 1", (chave,)
            ).fetchone()
            if existe:
                return None
        cur = conn.execute(
            "INSERT INTO notificacoes (tipo, mensagem, link, chave) VALUES (?, ?, ?, ?)",
            (tipo, mensagem, link, chave)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()