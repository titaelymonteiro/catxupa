from .db import get_connection

def relatorio_vendas_periodo(data_inicio, data_fim):
    """Retorna lista de vendas num intervalo de datas."""
    conn = get_connection()
    query = """
        SELECT * FROM vendas 
        WHERE DATE(criado_em) BETWEEN ? AND ?
        ORDER BY criado_em DESC
    """
    rows = conn.execute(query, (data_inicio, data_fim)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def relatorio_top_produtos(limite=10):
    """Retorna os produtos mais vendidos."""
    conn = get_connection()
    query = """
        SELECT medicamento_nome, SUM(quantidade) as total_qtd, SUM(subtotal) as total_valor
        FROM venda_itens
        GROUP BY medicamento_id
        ORDER BY total_qtd DESC
        LIMIT ?
    """
    rows = conn.execute(query, (limite,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def relatorio_vendas_por_utilizador():
    """Retorna o total de vendas por cada utilizador/funcionário."""
    conn = get_connection()
    query = """
        SELECT criado_por, COUNT(*) as n_vendas, SUM(total) as total_valor
        FROM vendas
        GROUP BY criado_por
        ORDER BY total_valor DESC
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]
