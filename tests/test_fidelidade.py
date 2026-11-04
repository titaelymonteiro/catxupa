"""Testes do programa de pontos de fidelidade."""
from conftest import criar_medicamento


def _criar_cliente_com_conta(client, email="fidelidade@example.com"):
    resp = client.post(
        "/registar",
        json={"nome": "Cliente Fidelidade", "email": email, "password": "1234"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _cliente_id_por_email(client, admin_headers, email):
    clientes = client.get("/clientes", headers=admin_headers).json()
    return next(c["id"] for c in clientes if c["email"] == email)


def _fazer_venda(client, admin_headers, med_id, cliente_id=None, preco=500.0,
                  quantidade=1, pontos_resgatados=0, metodo="visa"):
    subtotal = round(preco * quantidade, 2)
    payload = {
        "cliente": "Cliente Fidelidade",
        "cliente_id": cliente_id,
        "itens": [{
            "medicamento_id": med_id, "medicamento_nome": "Medicamento de Teste",
            "quantidade": quantidade, "preco_unitario": preco, "subtotal": subtotal,
        }],
        "pontos_resgatados": pontos_resgatados,
    }
    # calcular quanto falta pagar apos desconto de pontos (5 CVE por ponto)
    total_a_pagar = max(0, subtotal - pontos_resgatados * 5.0)
    payload["pagamentos"] = [{"metodo": metodo, "valor": total_a_pagar}] if total_a_pagar > 0 else [{"metodo": metodo, "valor": 0.01}]
    return client.post("/vendas", json=payload, headers=admin_headers)


def test_venda_com_cliente_ganha_pontos(client, admin_headers):
    headers = _criar_cliente_com_conta(client, "ganhapontos@example.com")
    cliente_id = _cliente_id_por_email(client, admin_headers, "ganhapontos@example.com")
    med_id = criar_medicamento(client, admin_headers, preco=500.0, estoque=10)

    resp = _fazer_venda(client, admin_headers, med_id, cliente_id=cliente_id, preco=500.0)
    assert resp.status_code == 201, resp.text

    fidelidade = client.get("/minha-fidelidade", headers=headers).json()
    assert fidelidade["saldo"] == 5  # 500 CVE / 100 = 5 pontos


def test_venda_sem_cliente_nao_ganha_pontos(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, preco=500.0, estoque=10)
    resp = client.post(
        "/vendas",
        json={
            "itens": [{
                "medicamento_id": med_id, "medicamento_nome": "Medicamento de Teste",
                "quantidade": 1, "preco_unitario": 500.0, "subtotal": 500.0,
            }],
            "pagamentos": [{"metodo": "visa", "valor": 500.0}],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201  # continua a funcionar normalmente, so nao gera pontos


def test_resgatar_pontos_aplica_desconto(client, admin_headers):
    headers = _criar_cliente_com_conta(client, "resgate@example.com")
    cliente_id = _cliente_id_por_email(client, admin_headers, "resgate@example.com")
    med_caro = criar_medicamento(client, admin_headers, nome="Med Caro Resgate", preco=1000.0, estoque=20)
    med_barato = criar_medicamento(client, admin_headers, nome="Med Barato Resgate", preco=100.0, estoque=20)

    # primeira compra: ganha 10 pontos (1000/100)
    _fazer_venda(client, admin_headers, med_caro, cliente_id=cliente_id, preco=1000.0)
    saldo_antes = client.get("/minha-fidelidade", headers=headers).json()["saldo"]
    assert saldo_antes == 10

    # segunda compra (medicamento de 100 CVE): resgata 4 pontos = 20 CVE de desconto -> paga 80
    resp = _fazer_venda(client, admin_headers, med_barato, cliente_id=cliente_id, preco=100.0, pontos_resgatados=4)
    assert resp.status_code == 201, resp.text

    saldo_depois = client.get("/minha-fidelidade", headers=headers).json()["saldo"]
    # -4 resgatados, +0 ganhos (100 - 20 = 80 CVE pagos, 80//100 = 0 pontos)
    assert saldo_depois == saldo_antes - 4


def test_resgatar_mais_pontos_do_que_tem_falha(client, admin_headers):
    headers = _criar_cliente_com_conta(client, "semsaldo@example.com")
    cliente_id = _cliente_id_por_email(client, admin_headers, "semsaldo@example.com")
    med_id = criar_medicamento(client, admin_headers, preco=100.0, estoque=10)

    resp = _fazer_venda(client, admin_headers, med_id, cliente_id=cliente_id, preco=100.0, pontos_resgatados=999)
    assert resp.status_code == 400
    assert "saldo" in resp.json()["detail"].lower()


def test_resgatar_pontos_sem_cliente_associado_falha(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, preco=100.0, estoque=10)
    resp = client.post(
        "/vendas",
        json={
            "itens": [{
                "medicamento_id": med_id, "medicamento_nome": "Medicamento de Teste",
                "quantidade": 1, "preco_unitario": 100.0, "subtotal": 100.0,
            }],
            "pagamentos": [{"metodo": "visa", "valor": 100.0}],
            "pontos_resgatados": 5,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_anular_venda_reverte_pontos_ganhos(client, admin_headers):
    headers = _criar_cliente_com_conta(client, "anularganho@example.com")
    cliente_id = _cliente_id_por_email(client, admin_headers, "anularganho@example.com")
    med_id = criar_medicamento(client, admin_headers, preco=500.0, estoque=10)

    resp = _fazer_venda(client, admin_headers, med_id, cliente_id=cliente_id, preco=500.0)
    venda_id = resp.json()["venda_id"]

    saldo_antes = client.get("/minha-fidelidade", headers=headers).json()["saldo"]
    assert saldo_antes == 5

    client.post(f"/vendas/{venda_id}/anular", json={"motivo": None}, headers=admin_headers)

    saldo_depois = client.get("/minha-fidelidade", headers=headers).json()["saldo"]
    assert saldo_depois == 0


def test_anular_venda_repoe_pontos_resgatados(client, admin_headers):
    headers = _criar_cliente_com_conta(client, "anularresgate@example.com")
    cliente_id = _cliente_id_por_email(client, admin_headers, "anularresgate@example.com")
    med_caro = criar_medicamento(client, admin_headers, nome="Med Caro Anular", preco=1000.0, estoque=20)
    med_barato = criar_medicamento(client, admin_headers, nome="Med Barato Anular", preco=100.0, estoque=20)

    _fazer_venda(client, admin_headers, med_caro, cliente_id=cliente_id, preco=1000.0)
    saldo_apos_primeira = client.get("/minha-fidelidade", headers=headers).json()["saldo"]
    assert saldo_apos_primeira == 10

    resp = _fazer_venda(client, admin_headers, med_barato, cliente_id=cliente_id, preco=100.0, pontos_resgatados=5)
    assert resp.status_code == 201, resp.text
    venda_id = resp.json()["venda_id"]

    saldo_apos_resgate = client.get("/minha-fidelidade", headers=headers).json()["saldo"]
    assert saldo_apos_resgate == 5  # 10 - 5

    client.post(f"/vendas/{venda_id}/anular", json={"motivo": None}, headers=admin_headers)

    saldo_apos_anular = client.get("/minha-fidelidade", headers=headers).json()["saldo"]
    assert saldo_apos_anular == 10  # os 5 resgatados voltam


def test_historico_de_pontos_regista_movimentos(client, admin_headers):
    headers = _criar_cliente_com_conta(client, "historicopontos@example.com")
    cliente_id = _cliente_id_por_email(client, admin_headers, "historicopontos@example.com")
    med_id = criar_medicamento(client, admin_headers, preco=500.0, estoque=10)

    _fazer_venda(client, admin_headers, med_id, cliente_id=cliente_id, preco=500.0)

    fidelidade = client.get("/minha-fidelidade", headers=headers).json()
    assert any(h["tipo"] == "ganho" for h in fidelidade["historico"])


def test_staff_consegue_ver_pontos_de_um_cliente(client, admin_headers):
    _criar_cliente_com_conta(client, "vercliente@example.com")
    cliente_id = _cliente_id_por_email(client, admin_headers, "vercliente@example.com")

    resp = client.get(f"/clientes/{cliente_id}/pontos", headers=admin_headers)
    assert resp.status_code == 200
    assert "saldo" in resp.json()


def test_minha_fidelidade_sem_conta_cliente_falha(client, funcionario_headers):
    resp = client.get("/minha-fidelidade", headers=funcionario_headers)
    assert resp.status_code == 400


def test_minha_fidelidade_sem_autenticacao_falha(client):
    resp = client.get("/minha-fidelidade")
    assert resp.status_code in (401, 403)