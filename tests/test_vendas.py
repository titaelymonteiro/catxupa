"""Testes de /vendas — a parte mais sensível da app (dinheiro e stock)."""
from conftest import criar_medicamento


def test_criar_venda_desconta_stock(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Xarope", preco=100.0, estoque=10)

    resp = client.post(
        "/vendas",
        json={
            "cliente": "Cliente Geral",
            "itens": [
                {
                    "medicamento_id": med_id,
                    "medicamento_nome": "Xarope",
                    "quantidade": 3,
                    "preco_unitario": 100.0,
                    "subtotal": 300.0,
                }
            ],
            "pagamentos": [{"metodo": "visa", "valor": 300.0}],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text

    med = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert med["estoque"] == 7  # 10 - 3


def test_criar_venda_sem_stock_suficiente_falha(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Colírio", estoque=2)

    resp = client.post(
        "/vendas",
        json={
            "itens": [
                {
                    "medicamento_id": med_id,
                    "medicamento_nome": "Colírio",
                    "quantidade": 5,
                    "preco_unitario": 150.0,
                    "subtotal": 750.0,
                }
            ],
            "pagamentos": [{"metodo": "visa", "valor": 750.0}],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400

    # o stock não deve ter sido alterado
    med = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert med["estoque"] == 2


def test_venda_ignora_preco_enviado_pelo_cliente(client, admin_headers):
    """O preço/subtotal vindos do browser nunca devem ser usados — o
    servidor tem de recalcular tudo a partir do preço guardado na BD."""
    med_id = criar_medicamento(client, admin_headers, nome="Aspirina", preco=50.0, estoque=10)

    resp = client.post(
        "/vendas",
        json={
            "itens": [
                {
                    "medicamento_id": med_id,
                    "medicamento_nome": "Aspirina",
                    "quantidade": 2,
                    "preco_unitario": 1.0,   # tentativa de fraude
                    "subtotal": 2.0,          # tentativa de fraude
                }
            ],
            # paga o valor "fraudado" (2 CVE) — deve falhar porque o
            # servidor recalcula o total real como 100 CVE (2 x 50)
            "pagamentos": [{"metodo": "visa", "valor": 2.0}],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "Falta pagar" in resp.json()["detail"]


def test_venda_sem_itens_falha(client, admin_headers):
    resp = client.post(
        "/vendas",
        json={"itens": [], "pagamentos": [{"metodo": "visa", "valor": 10.0}]},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_venda_sem_pagamentos_falha(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    resp = client.post(
        "/vendas",
        json={
            "itens": [
                {
                    "medicamento_id": med_id,
                    "medicamento_nome": "Medicamento de Teste",
                    "quantidade": 1,
                    "preco_unitario": 150.0,
                    "subtotal": 150.0,
                }
            ],
            "pagamentos": [],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_venda_metodo_pagamento_invalido_falha(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    resp = client.post(
        "/vendas",
        json={
            "itens": [
                {
                    "medicamento_id": med_id,
                    "medicamento_nome": "Medicamento de Teste",
                    "quantidade": 1,
                    "preco_unitario": 150.0,
                    "subtotal": 150.0,
                }
            ],
            "pagamentos": [{"metodo": "bitcoin", "valor": 150.0}],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_venda_medicamento_inexistente_falha(client, admin_headers):
    resp = client.post(
        "/vendas",
        json={
            "itens": [
                {
                    "medicamento_id": 999999,
                    "medicamento_nome": "Não existe",
                    "quantidade": 1,
                    "preco_unitario": 10.0,
                    "subtotal": 10.0,
                }
            ],
            "pagamentos": [{"metodo": "visa", "valor": 10.0}],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_listar_e_obter_venda(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    criar = client.post(
        "/vendas",
        json={
            "itens": [
                {
                    "medicamento_id": med_id,
                    "medicamento_nome": "Medicamento de Teste",
                    "quantidade": 1,
                    "preco_unitario": 150.0,
                    "subtotal": 150.0,
                }
            ],
            "pagamentos": [{"metodo": "visa", "valor": 150.0}],
        },
        headers=admin_headers,
    )
    venda_id = criar.json()["venda_id"]

    resp = client.get(f"/vendas/{venda_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()["itens"]) == 1

    resp = client.get("/vendas", headers=admin_headers)
    assert resp.status_code == 200
    assert any(v["id"] == venda_id for v in resp.json())


def _criar_venda_simples(client, admin_headers, med_id, quantidade=2, preco=150.0):
    subtotal = round(quantidade * preco, 2)
    resp = client.post(
        "/vendas",
        json={
            "itens": [
                {
                    "medicamento_id": med_id,
                    "medicamento_nome": "Medicamento de Teste",
                    "quantidade": quantidade,
                    "preco_unitario": preco,
                    "subtotal": subtotal,
                }
            ],
            "pagamentos": [{"metodo": "visa", "valor": subtotal}],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["venda_id"]


def test_anular_venda_repoe_o_stock(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, estoque=20)
    venda_id = _criar_venda_simples(client, admin_headers, med_id, quantidade=5)

    depois_da_venda = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert depois_da_venda["estoque"] == 15

    resp = client.post(
        f"/vendas/{venda_id}/anular", json={"motivo": "cliente desistiu"}, headers=admin_headers
    )
    assert resp.status_code == 200, resp.text

    depois_de_anular = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert depois_de_anular["estoque"] == 20


def test_venda_anulada_aparece_marcada_ao_consultar(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    venda_id = _criar_venda_simples(client, admin_headers, med_id)

    client.post(f"/vendas/{venda_id}/anular", json={"motivo": "erro de registo"}, headers=admin_headers)

    venda = client.get(f"/vendas/{venda_id}", headers=admin_headers).json()
    assert venda["anulada"] == 1
    assert venda["anulada_por"] == "admin@farmacia.cv"
    assert venda["motivo_anulacao"] == "erro de registo"


def test_anular_venda_duas_vezes_falha(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    venda_id = _criar_venda_simples(client, admin_headers, med_id)

    primeira = client.post(f"/vendas/{venda_id}/anular", json={"motivo": None}, headers=admin_headers)
    assert primeira.status_code == 200

    segunda = client.post(f"/vendas/{venda_id}/anular", json={"motivo": None}, headers=admin_headers)
    assert segunda.status_code == 400


def test_anular_venda_inexistente_devolve_404(client, admin_headers):
    resp = client.post("/vendas/999999/anular", json={"motivo": None}, headers=admin_headers)
    assert resp.status_code == 404


def test_funcionario_nao_pode_anular_venda(client, admin_headers, funcionario_headers):
    """Anular vendas é restrito a admin, mesmo sendo staff."""
    med_id = criar_medicamento(client, admin_headers)
    venda_id = _criar_venda_simples(client, admin_headers, med_id)

    resp = client.post(f"/vendas/{venda_id}/anular", json={"motivo": None}, headers=funcionario_headers)
    assert resp.status_code == 403

    # confirma que o stock não foi mexido pela tentativa falhada
    venda = client.get(f"/vendas/{venda_id}", headers=admin_headers).json()
    assert venda["anulada"] == 0


def test_anular_venda_gera_log(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    venda_id = _criar_venda_simples(client, admin_headers, med_id)

    client.post(f"/vendas/{venda_id}/anular", json={"motivo": "teste"}, headers=admin_headers)

    logs = client.get("/logs", headers=admin_headers).json()
    assert any(
        log["acao"] == "anular" and log["entidade"] == "venda" and log["entidade_id"] == str(venda_id)
        for log in logs
    )