"""Programa de pontos de fidelidade.

Regras:
- Ganho: 1 ponto por cada 100 CVE gastos (sobre o total já com descontos).
- Resgate: cada ponto vale 5 CVE de desconto.

O saldo de cada cliente vive na coluna `clientes.pontos_fidelidade` e cada
movimento (ganho / resgate / ajuste) fica registado na tabela
`pontos_historico`. Este módulo só trata do cálculo e da leitura; as
atualizações de saldo são feitas dentro da transação da venda
(`venda_model.criar_venda` / anulação), para nunca deixar o saldo negativo.
"""
from .db import get_connection

# Cada ponto resgatado vale este valor em CVE de desconto.
VALOR_POR_PONTO = 5.0

# É preciso gastar este valor (em CVE) para ganhar 1 ponto.
CVE_POR_PONTO = 100


def calcular_pontos_ganhos(total: float) -> int:
    """Pontos ganhos numa compra: 1 ponto por cada 100 CVE do total pago.
    Ex.: 500 CVE -> 5 pontos; 80 CVE -> 0 pontos."""
    if not total or total <= 0:
        return 0
    return int(total // CVE_POR_PONTO)


def calcular_desconto(pontos: int) -> float:
    """Desconto em CVE ao resgatar `pontos` pontos (5 CVE por ponto)."""
    if not pontos or pontos <= 0:
        return 0.0
    return round(pontos * VALOR_POR_PONTO, 2)


def obter_saldo(cliente_id: int) -> int:
    """Saldo atual de pontos de fidelidade de um cliente."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT pontos_fidelidade FROM clientes WHERE id = ?", (cliente_id,)
        ).fetchone()
        return row["pontos_fidelidade"] if row else 0
    finally:
        conn.close()


def listar_historico(cliente_id: int, limite: int = 100) -> list:
    """Movimentos de pontos de um cliente, dos mais recentes para os mais antigos."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, tipo, pontos, motivo, venda_id, criado_em
               FROM pontos_historico
               WHERE cliente_id = ?
               ORDER BY id DESC
               LIMIT ?""",
            (cliente_id, limite)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()