"""Testes de /lotes — registo de lotes de fabrico e o efeito no stock."""
from conftest import criar_medicamento


def _criar_fornecedor(client, admin_headers, nome="Fornecedor Lote Teste"):
    resp = client.post(
        "/fornecedores",
        json={
            "nome": nome,
            "nif": "1",
            "telefone": "1",
            "email": "a@a.cv",
            "endereco": "X",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    listagem = client.get("/fornecedores", headers=admin_headers).json()
    candidatos = [f for f in listagem if f["nome"] == nome]
    return max(candidatos, key=lambda f: f["id"])["id"]

def test_criar_lote_aumenta_o_stock(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, estoque=20)
    fornecedor_id = _criar_fornecedor(client, admin_headers)
    
    resp = client.post(
        "/lotes",
        json={
            "medicamento_id": med_id,
            "fornecedor_id": fornecedor_id,
            "numero_lote": "LOTE-001",
            "quantidade": 15,
            "validade": "2027-06-01",
            "preco_custo": 80.0,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    
    med = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert med["estoque"] == 35 # 20 + 15
    
    
def test_criar_lote_sem_fornecedor_e_permitido(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, estoque=5)
    
    resp = client.post(
        "/lotes",
        json={
            "medicamento_id": med_id,
            "numero_lote": "LOTE-SEM-FORN",
            "quantidade": 10,
            "validade": "2027-06-01",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    
    
def test_criar_lote_medicamento_inexistente_falha(client, admin_headers):
    resp = client.post(
        "/lotes",
        json={
            "medicamento_id": 999999,
            "numero_lote": "LOTE-X",
            "quantidade": 10,
            "validade": "2027-06-01",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 404
    
    
def test_criar_lote_fornecedor_inexistente_falha(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    resp = client.post(
        "/lotes",
        json={
            "medicamento_id": med_id,
            "fornecedor_id": 999999,
            "numero_lote": "LOTE-Y",
            "quantidade": 10,
            "validade": "2027-06-01",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 404
    
    
def test_apagar_lote_desconta_stock(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, estoque=10)
    
    criar = client.post(
        "/lotes",
        json={
            "medicamento_id": med_id,
            "numero_lote": "LOTE-APAGAR",
            "quantidade": 20,
            "validade": "2027-06-01",
        },
        headers=admin_headers,
    )
    lote_id = criar.json()["lote_id"]
    
    
    med = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert med["estoque"] == 30
    
    resp = client.delete(f"/lotes/{lote_id}", headers=admin_headers)
    assert resp.status_code == 200
    
    med = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert med["estoque"] == 10
    
    
def test_apagar_lote_nao_deixa_stock_negativo(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, estoque=2)
    
    criar = client.post(
        "/lotes",
        json={
            "medicamento_id": med_id,
            "numero_lote": "LOTE-NEG",
            "quantidade": 5,
            "validade": "2027-06-01",
        },
        headers=admin_headers,
    )
    lote_id = criar.json()["lote_id"]
    
    
    # entretanto o stock desce por outra via (ex: vendas) para menos do que o lote tinha
    client.put(
        f"/medicamentos/{med_id}",
        json={"nome": "Medicamento de Teste", "preco": 150.0, "estoque": 1},
        headers=admin_headers,
    )
    
    resp = client.delete(f"/lotes/{lote_id}", headers=admin_headers)
    assert resp.status_code == 200
    
    med = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert med["estoque"] == 0 # nunca fica negativo
    
    
def test_listar_lotes_por_medicamento(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    client.post(
        "/lotes",
        json={
            "medicamento_id": med_id,
            "numero_lote": "LOTE-LISTAR",
            "quantidade": 5,
            "validade": "2027-06-01",
        },
        headers=admin_headers,
    )
    
    resp = client.get(f"/medicamentos/{med_id}/lotes", headers=admin_headers)
    assert resp.status_code == 200
    numeros = [l["numero_lote"] for l in resp.json()]
    assert "LOTE-LISTAR" in numeros
    
    
def test_funcionario_pode_gerir_lotes(client, funcionario_headers, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    resp = client.post(
        "/lotes",
        json={
            "medicamento_id": med_id,
            "numero_lote": "LOTE-FUNC",
            "quantidade": 5,
            "validade": "2027-06-01",
        },
        headers=funcionario_headers,
    )
    assert resp.status_code == 201
    
    
def test_cliente_nao_pode_gerir_lotes(client, cliente_headers):
    resp = client.get("/lotes", headers=cliente_headers)
    assert resp.status_code == 403
    
    
def test_lote_gera_log(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    client.post(
        "/lotes",
        json={
            "medicamento_id": med_id,
            "numero_lote": "LOTE-LOG",
            "quantidade": 5,
            "validade": "2027-06-01",
        },
        headers=admin_headers,
    )
    logs = client.get("/logs", headers=admin_headers).json()
    assert any(log["acao"] == "criar" and log["entidade"] == "lote" for log in logs)