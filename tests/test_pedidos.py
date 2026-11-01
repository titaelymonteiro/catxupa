"""Testes de /pedidos, /meus-pedidos e /catalogo — encomendas online de clientes."""
from conftest import criar_medicamento



def _registar_cliente_com_pedido_pronto(client, admin_headers, email="pedidos.teste@example.com"):
    """Regista uma conta cliente e devolve os headers de autenticação."""
    resp = client.post(
        "/registar",
        json={"nome": "Cliente Pedidos", "email": email, "password": "1234"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_catalogo_visivel_para_qualquer_autenticado(client, cliente_headers):
    resp = client.get("/catalogo", headers=cliente_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    
    
def test_catalogo_nao_expoe_quantidade_exata_de_stock(client, cliente_headers, admin_headers):
    criar_medicamento(client, admin_headers, nome="Medicamento Catalogo", estoque=7)
    resp = client.get("/catalogo", headers=cliente_headers)
    item = next(m for m in resp.json() if m["nome"] == "Medicamento Catalogo")
    assert "estoque" not in item
    assert item["disponivel"] is True
    
    
def test_catalogo_sem_autenticacao_falha(client):
    resp = client.get("/catalogo")
    assert resp.status_code in (401, 403)
    
    
def test_criar_pedido_com_sucesso(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Med Pedido A", preco=150.0, estoque=20)
    
    resp = client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 2}]},
        headers=cliente_headers,
    )
    assert resp.status_code == 201, resp.text
    assert "pedido_id" in resp.json()
    
    
def test_criar_pedido_nao_desconta_stock_de_imediato(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Med Pedido B", preco=100.0, estoque=15)
    
    client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 3}]},
        headers=cliente_headers,
    )
    
    med = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert med["estoque"] == 15 # ainda nao descontou
    
    
def test_criar_pedido_recalcula_preco_no_servidor(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Med Pedido Preco", preco=200.0, estoque=10)
    
    resp = client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 2}]},
        headers=cliente_headers,
    )
    pedido_id = resp.json()["pedido_id"]
    
    pedidos = client.get("/pedidos", headers=admin_headers).json()
    pedido = next(p for p in pedidos if p["id"] == pedido_id)
    assert pedido["total"] == 400.0 # 2 x 200, nunca enviado pelo cliente
    
    
def test_criar_pedido_medicamento_inexistente_falha(client, cliente_headers):
    resp = client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": 999999, "quantidade": 1}]},
        headers=cliente_headers,
    )
    assert resp.status_code == 400
    
    
def test_criar_pedido_sem_itens_falha(client, cliente_headers):
    resp = client.post("/pedidos", json={"itens": []}, headers=cliente_headers)
    assert resp.status_code == 400
    
    
def test_criar_pedido_quantidade_zero_falha(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers)
    resp = client.post(
        "pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 0}]},
        headers=cliente_headers,
    )
    assert resp.status_code == 400
    
    
def test_funcionario_nao_pode_fazer_pedido(client, funcionario_headers, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    resp = client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 1}]},
        headers=funcionario_headers,
    )
    assert resp.status_code == 400 # conta de staff nao tem cliente_id associado
    
    
def test_meus_pedidos_mostra_apenas_os_proprios(client, admin_headers):
    cliente_a = _registar_cliente_com_pedido_pronto(client, admin_headers, "clientea@example.com")
    cliente_b = _registar_cliente_com_pedido_pronto(client, admin_headers, "clienteb@example.com")
    med_id = criar_medicamento(client, admin_headers, estoque=20)
    
    
    client.post("/pedidos", json={"itens": [{"medicamento_id": med_id, "quantidade": 1}]}, headers=cliente_a)
    client.post("/pedidos", json={"itens": [{"medicamento_id": med_id, "quantidade": 1}]}, headers=cliente_b)
    
    pedidos_a = client.get("/meus-pedidos", headers=cliente_a).json()
    assert len(pedidos_a) == 1
    
    
def test_staff_ve_todos_os_pedidos(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, estoque=20)
    client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 1}]},
        headers=cliente_headers,
    )
    
    resp = client.get("/pedidos", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    
    
def test_cliente_nao_pode_ver_pedidos_de_outros(client, cliente_headers):
    resp = client.get("/pedidos", headers=cliente_headers)
    assert resp.status_code == 403
    
    
def test_confirmar_pedido_desconta_stock(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Med Confirmar", preco=100.0, estoque=10)
    
    
    criar = client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 4}]},
        headers=cliente_headers,
    )
    pedido_id = criar.json()["pedido_id"]
    
    resp = client.put(f"/pedidos/{pedido_id}/estado", json={"estado": "confirmado"}, headers=admin_headers)
    assert resp.status_code == 200
    
    med = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert med["estoque"] == 6 # 10 - 4
    
    
def test_confirmar_pedido_sem_stock_suficiente_falha(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Med Sem Stock", preco=100.0, estoque=2)
    
    criar = client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 5}]},
        headers=cliente_headers,
    )
    pedido_id = criar.json()["pedido_id"]
    
    
    resp = client.put(f"/pedidos/{pedido_id}/estado", json={"estado": "confirmado"}, headers=admin_headers)
    assert resp.status_code == 400
    
    
    med = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert med["estoque"] == 2 # inalterado
    
    
def test_cancelar_pedido_confirmado_repoe_stock(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Med Cancelar Confirmado", preco=100.0, estoque=10)
    
    
    criar = client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 3}]},
        headers=cliente_headers,
    )
    pedido_id = criar.json()["pedido_id"]
    client.put(f"/pedidos/{pedido_id}/estado", json={"estado": "confirmado"}, headers=admin_headers)
    
    med_apos_confirmar = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert med_apos_confirmar["estoque"] == 7
    
    client.put(f"/pedidos/{pedido_id}/estado", json={"estado": "cancelado"}, headers=admin_headers)
    
    med_apos_cancelar = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert med_apos_cancelar["estoque"] == 10 # reposto
    
    
def test_cliente_pode_cancelar_pedido_pendente(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, estoque=10)
    criar = client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 2}]},
        headers=cliente_headers,
    )
    pedido_id = criar.json()["pedido_id"]
    
    
    resp = client.post(f"/meus-pedidos/{pedido_id}/cancelar", headers=cliente_headers)
    assert resp.status_code == 200
    
    
def test_client_nao_pode_cancelar_pedido_ja_confirmado(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, estoque=10)
    criar = client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 2}]},
        headers=cliente_headers,
    )
    pedido_id = criar.json()["pedido_id"]
    client.put(f"/pedidos/{pedido_id}/estado", json={"estado": "confirmado"}, headers=admin_headers)
    
    resp = client.post(f"/meus-pedidos/{pedido_id}/cancelar", headers=cliente_headers)
    assert resp.status_code == 400
    
    
def test_nao_e_possivel_alterar_pedido_ja_concluido(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, estoque=10)
    criar = client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 1}]},
        headers=cliente_headers,
    )
    pedido_id = criar.json()["pedido_id"]
    client.put(f"/pedidos/{pedido_id}/estado", json={"estado": "confirmado"}, headers=admin_headers)
    client.put(f"/pedidos/{pedido_id}/estado", json={"estado": "pronto"}, headers=admin_headers)
    client.put(f"/pedidos/{pedido_id}/estado", json={"estado": "concluido"}, headers=admin_headers)
 
    resp = client.put(f"/pedidos/{pedido_id}/estado", json={"estado": "cancelado"}, headers=admin_headers)
    assert resp.status_code == 400
 
 
def test_estado_invalido_falha(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, estoque=10)
    criar = client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 1}]},
        headers=cliente_headers,
    )
    pedido_id = criar.json()["pedido_id"]
 
    resp = client.put(f"/pedidos/{pedido_id}/estado", json={"estado": "isto-nao-existe"}, headers=admin_headers)
    assert resp.status_code == 400
 
 
def test_funcionario_pode_gerir_pedidos(client, admin_headers, funcionario_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, estoque=10)
    criar = client.post(
        "/pedidos",
        json={"itens": [{"medicamento_id": med_id, "quantidade": 1}]},
        headers=cliente_headers,
    )
    pedido_id = criar.json()["pedido_id"]
 
    resp = client.put(f"/pedidos/{pedido_id}/estado", json={"estado": "confirmado"}, headers=funcionario_headers)
    assert resp.status_code == 200
 
 
def test_pedido_gera_log(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, estoque=10)
    client.post("/pedidos", json={"itens": [{"medicamento_id": med_id, "quantidade": 1}]}, headers=cliente_headers)
 
    logs = client.get("/logs", headers=admin_headers).json()
    assert any(log["acao"] == "criar" and log["entidade"] == "pedido" for log in logs)
 
 
def test_pedidos_sem_autenticacao_falha(client):
    resp = client.get("/pedidos")
    assert resp.status_code in (401, 403)
 
    resp2 = client.get("/meus-pedidos")
    assert resp2.status_code in (401, 403)