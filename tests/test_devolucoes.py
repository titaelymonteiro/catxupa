"""Testes de devolucoes de vendas e da receita liquida no dashboard."""
from conftest import criar_medicamento, criar_venda


def _estoque(client, headers, med_id):
    return client.get(f"/medicamentos/{med_id}", headers=headers).json()["estoque"]


def test_devolver_repoe_stock(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="MedDev", preco=200.0, estoque=20)
    venda_id = criar_venda(client, admin_headers, med_id, "MedDev", quantidade=5, preco_unitario=200.0)
    assert _estoque(client, admin_headers, med_id) == 15

    resp = client.post(
        f"/vendas/{venda_id}/devolucao",
        json={"medicamento_id": med_id, "quantidade": 2},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["valor"] == 400.0
    assert _estoque(client, admin_headers, med_id) == 17


def test_nao_devolve_mais_do_que_vendido(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="MedDev2", preco=100.0, estoque=10)
    venda_id = criar_venda(client, admin_headers, med_id, "MedDev2", quantidade=3, preco_unitario=100.0)
    resp = client.post(
        f"/vendas/{venda_id}/devolucao",
        json={"medicamento_id": med_id, "quantidade": 4},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_nao_devolve_de_venda_anulada(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="MedDev3", preco=100.0, estoque=10)
    venda_id = criar_venda(client, admin_headers, med_id, "MedDev3", quantidade=2, preco_unitario=100.0)
    client.post(f"/vendas/{venda_id}/anular", json={"motivo": "teste"}, headers=admin_headers)
    resp = client.post(
        f"/vendas/{venda_id}/devolucao",
        json={"medicamento_id": med_id, "quantidade": 1},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_devolucao_aparece_no_detalhe(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="MedDev4", preco=150.0, estoque=10)
    venda_id = criar_venda(client, admin_headers, med_id, "MedDev4", quantidade=4, preco_unitario=150.0)
    client.post(
        f"/vendas/{venda_id}/devolucao",
        json={"medicamento_id": med_id, "quantidade": 1, "motivo": "danificado"},
        headers=admin_headers,
    )
    venda = client.get(f"/vendas/{venda_id}", headers=admin_headers).json()
    assert venda["total_devolvido"] == 150.0
    assert len(venda["devolucoes"]) == 1
    item = next(i for i in venda["itens"] if i["medicamento_id"] == med_id)
    assert item["qtd_devolvida"] == 1


def test_receita_liquida_desconta_devolucoes(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="MedRL", preco=200.0, estoque=20)
    venda_id = criar_venda(client, admin_headers, med_id, "MedRL", quantidade=5, preco_unitario=200.0)  # 1000
    client.post(
        f"/vendas/{venda_id}/devolucao",
        json={"medicamento_id": med_id, "quantidade": 2},  # -400
        headers=admin_headers,
    )
    dash = client.get("/dashboard", headers=admin_headers).json()
    assert dash["receita_liquida"] == 600.0
    assert dash["total_devolvido"] == 400.0


def test_anular_com_devolucao_nao_duplica_stock(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="MedDup", preco=100.0, estoque=20)
    venda_id = criar_venda(client, admin_headers, med_id, "MedDup", quantidade=5, preco_unitario=100.0)  # 15
    client.post(
        f"/vendas/{venda_id}/devolucao",
        json={"medicamento_id": med_id, "quantidade": 2},  # 17
        headers=admin_headers,
    )
    client.post(f"/vendas/{venda_id}/anular", json={"motivo": "x"}, headers=admin_headers)
    # repoe so os 3 que ainda estavam fora -> 20, e nao 22
    assert _estoque(client, admin_headers, med_id) == 20


def test_receita_liquida_nao_fica_negativa_ao_anular(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="MedNeg", preco=200.0, estoque=20)
    venda_id = criar_venda(client, admin_headers, med_id, "MedNeg", quantidade=5, preco_unitario=200.0)
    client.post(
        f"/vendas/{venda_id}/devolucao",
        json={"medicamento_id": med_id, "quantidade": 2},
        headers=admin_headers,
    )
    client.post(f"/vendas/{venda_id}/anular", json={"motivo": "x"}, headers=admin_headers)
    dash = client.get("/dashboard", headers=admin_headers).json()
    assert dash["receita_liquida"] == 0.0


def test_funcionario_pode_devolver(client, admin_headers, funcionario_headers):
    med_id = criar_medicamento(client, admin_headers, nome="MedFunc", preco=100.0, estoque=10)
    venda_id = criar_venda(client, admin_headers, med_id, "MedFunc", quantidade=3, preco_unitario=100.0)
    resp = client.post(
        f"/vendas/{venda_id}/devolucao",
        json={"medicamento_id": med_id, "quantidade": 1},
        headers=funcionario_headers,
    )
    assert resp.status_code == 200