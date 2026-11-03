"""Testes de /relatorios/*."""
import datetime

from conftest import criar_medicamento, criar_venda


def _hoje():
    return datetime.date.today().isoformat()


def _amanha():
    return (datetime.date.today() + datetime.timedelta(days=1)).isoformat()


def test_relatorio_vendas_por_periodo_inclui_venda_de_hoje(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    criar_venda(client, admin_headers, med_id)

    resp = client.get(
        "/relatorios/vendas",
        params={"inicio": _hoje(), "fim": _amanha()},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_relatorio_vendas_por_periodo_fora_do_intervalo_fica_vazio(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    criar_venda(client, admin_headers, med_id)

    ano_passado = str(datetime.date.today().year - 1)
    resp = client.get(
        "/relatorios/vendas",
        params={"inicio": f"{ano_passado}-01-01", "fim": f"{ano_passado}-12-31"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_relatorio_vendas_sem_parametros_obrigatorios_falha(client, admin_headers):
    resp = client.get("/relatorios/vendas", headers=admin_headers)
    assert resp.status_code == 422  # inicio/fim são obrigatórios


def test_relatorio_top_produtos(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Produto Mais Vendido")
    criar_venda(client, admin_headers, med_id, medicamento_nome="Produto Mais Vendido", quantidade=4)

    resp = client.get("/relatorios/top-produtos", headers=admin_headers)
    assert resp.status_code == 200
    nomes = [p["medicamento_nome"] for p in resp.json()]
    assert "Produto Mais Vendido" in nomes


def test_relatorio_pagamentos_agrega_por_metodo(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    criar_venda(client, admin_headers, med_id, metodo="visa")
    criar_venda(client, admin_headers, med_id, metodo="cartao24")

    resp = client.get("/relatorios/pagamentos", headers=admin_headers)
    assert resp.status_code == 200
    metodos = {p["metodo"] for p in resp.json()}
    assert {"visa", "cartao24"} <= metodos


def test_relatorio_utilizadores_agrega_por_criado_por(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    criar_venda(client, admin_headers, med_id)

    resp = client.get("/relatorios/utilizadores", headers=admin_headers)
    assert resp.status_code == 200
    autores = [u["criado_por"] for u in resp.json()]
    assert "admin@farmacia.cv" in autores


def test_relatorios_acessiveis_a_funcionario(client, funcionario_headers):
    resp = client.get(
        "/relatorios/vendas",
        params={"inicio": _hoje(), "fim": _amanha()},
        headers=funcionario_headers,
    )
    assert resp.status_code == 200


def test_relatorios_bloqueados_para_cliente(client, cliente_headers):
    resp = client.get(
        "/relatorios/vendas",
        params={"inicio": _hoje(), "fim": _amanha()},
        headers=cliente_headers,
    )
    assert resp.status_code == 403


def test_relatorios_sem_autenticacao_falha(client):
    resp = client.get("/relatorios/top-produtos")
    assert resp.status_code in (401, 403)


def test_relatorio_margem_calcula_lucro_corretamente(client, admin_headers):
    med_id = criar_medicamento(
        client, admin_headers, nome="Medicamento Margem A", preco=200.0, estoque=20,
        preco_custo=120.0
    )
    criar_venda(client, admin_headers, med_id, medicamento_nome="Medicamento Margem A", quantidade=3, preco_unitario=200.0)

    resp = client.get("/relatorios/margem", headers=admin_headers)
    assert resp.status_code == 200
    dados = resp.json()

    produto = next(p for p in dados["produtos"] if p["medicamento_nome"] == "Medicamento Margem A")
    assert produto["quantidade_vendida"] == 3
    assert produto["receita"] == 600.0   # 3 x 200
    assert produto["custo"] == 360.0     # 3 x 120
    assert produto["lucro"] == 240.0     # 600 - 360
    assert produto["margem_pct"] == 40.0  # 240/600 = 40%


def test_relatorio_margem_exclui_vendas_anuladas(client, admin_headers):
    med_id = criar_medicamento(
        client, admin_headers, nome="Medicamento Margem Anulada", preco=100.0, estoque=10,
        preco_custo=50.0
    )
    venda_id = criar_venda(client, admin_headers, med_id, medicamento_nome="Medicamento Margem Anulada", quantidade=2, preco_unitario=100.0)
    client.post(f"/vendas/{venda_id}/anular", json={"motivo": None}, headers=admin_headers)

    resp = client.get("/relatorios/margem", headers=admin_headers)
    dados = resp.json()
    nomes = [p["medicamento_nome"] for p in dados["produtos"]]
    assert "Medicamento Margem Anulada" not in nomes


def test_relatorio_margem_assinala_medicamento_sem_custo_definido(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Medicamento Sem Custo", preco=80.0, estoque=10)
    criar_venda(client, admin_headers, med_id, medicamento_nome="Medicamento Sem Custo", quantidade=2, preco_unitario=80.0)

    resp = client.get("/relatorios/margem", headers=admin_headers)
    dados = resp.json()
    produto = next(p for p in dados["produtos"] if p["medicamento_nome"] == "Medicamento Sem Custo")
    assert produto["unidades_sem_custo"] == 2
    assert produto["custo"] == 0.0
    assert dados["resumo"]["unidades_sem_custo_definido"] >= 2


def test_relatorio_margem_resumo_agrega_tudo(client, admin_headers):
    med_id = criar_medicamento(
        client, admin_headers, nome="Medicamento Margem Resumo", preco=150.0, estoque=10,
        preco_custo=100.0
    )
    criar_venda(client, admin_headers, med_id, medicamento_nome="Medicamento Margem Resumo", quantidade=2, preco_unitario=150.0)

    resp = client.get("/relatorios/margem", headers=admin_headers)
    resumo = resp.json()["resumo"]
    assert resumo["receita_total"] >= 300.0
    assert resumo["lucro_total"] == resumo["receita_total"] - resumo["custo_total"]


def test_relatorio_margem_respeita_periodo(client, admin_headers):
    import datetime
    med_id = criar_medicamento(client, admin_headers, nome="Medicamento Margem Periodo", preco=100.0, estoque=10, preco_custo=50.0)
    criar_venda(client, admin_headers, med_id, medicamento_nome="Medicamento Margem Periodo", quantidade=1, preco_unitario=100.0)

    ano_passado = str(datetime.date.today().year - 1)
    resp = client.get(
        "/relatorios/margem",
        params={"inicio": f"{ano_passado}-01-01", "fim": f"{ano_passado}-12-31"},
        headers=admin_headers,
    )
    nomes = [p["medicamento_nome"] for p in resp.json()["produtos"]]
    assert "Medicamento Margem Periodo" not in nomes


def test_relatorio_margem_bloqueado_para_funcionario(client, funcionario_headers):
    resp = client.get("/relatorios/margem", headers=funcionario_headers)
    assert resp.status_code == 403


def test_relatorio_margem_bloqueado_para_cliente(client, cliente_headers):
    resp = client.get("/relatorios/margem", headers=cliente_headers)
    assert resp.status_code == 403


def test_relatorio_margem_sem_autenticacao_falha(client):
    resp = client.get("/relatorios/margem")
    assert resp.status_code in (401, 403)