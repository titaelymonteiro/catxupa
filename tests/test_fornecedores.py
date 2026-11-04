"""Testes do CRUD de fornecedores."""
 
 
def _criar_fornecedor(client, admin_headers, **overrides):
    dados = {
        "nome": "Farmadis Lda",
        "nif": "123456789",
        "telefone": "2381234",
        "email": "geral@farmadis.cv",
        "endereco": "Praia, Cabo Verde",
    }
    dados.update(overrides)
    resp = client.post("/fornecedores", json=dados, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    listagem = client.get("/fornecedores", headers=admin_headers).json()
    candidatos = [f for f in listagem if f["nome"] == dados["nome"]]
    return max(candidatos, key=lambda f: f["id"])["id"]


def test_criar_e_listar_fornecedor(client, admin_headers):
    fornecedor_id = _criar_fornecedor(client, admin_headers)
    resp = client.get("/fornecedores", headers=admin_headers)
    assert resp.status_code == 200
    assert any(f["id"] == fornecedor_id for f in resp.json())
    
    
def test_obter_fornecedor_inexistente_devolve_404(client, admin_headers):
    resp = client.get("/fornecedores/999999", headers=admin_headers)
    assert resp.status_code == 404
    
    
def test_editar_fornecedor(client, admin_headers):
    fornecedor_id = _criar_fornecedor(client, admin_headers, nome="Farmadis Antigo")
    
    resp = client.put(
        f"/fornecedores/{fornecedor_id}",
        json={
            "nome": "Farmadis Novo Nome",
            "nif": "987654321",
            "telefone": "238999999",
            "email": "novo@efarmadis.cv",
            "endereco": "Mindelo, Cabo Verde",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    
    atualizado = client.get(f"/fornecedores/{fornecedor_id}", headers=admin_headers).json()
    assert atualizado["nome"] == "Farmadis Novo Nome"
    
    
def test_apagar_fornecedor_sem_lotes(client, admin_headers):
    fornecedor_id = _criar_fornecedor(client, admin_headers)
    resp = client.delete(f"/fornecedores/{fornecedor_id}", headers=admin_headers)
    assert resp.status_code == 200
    
    resp = client.get(f"/fornecedores/{fornecedor_id}", headers=admin_headers)
    assert resp.status_code == 404
    
    
def test_apagar_fornecedor_com_lotes_falha(client, admin_headers):
    from conftest import criar_medicamento
    fornecedor_id = _criar_fornecedor(client, admin_headers, nome="Fornecedor Com Lote")
    med_id = criar_medicamento(client, admin_headers)
    
    client.post(
        "/lotes",
        json={
            "medicamento_id": med_id,
            "fornecedor_id": fornecedor_id,
            "numero_lote": "L001",
            "quantidade": 10,
            "validade": "2027-01-01",
            "preco_custo": 50.0,
        },
        headers=admin_headers,
    )
    
    resp = client.delete(f"/fornecedores/{fornecedor_id}", headers=admin_headers)
    assert resp.status_code == 400
    
    
def test_fornecedores_sem_auntenticacao_falha(client):
    resp = client.get("/fornecedores")
    assert resp.status_code in (401, 403)
    
    
def test_cliente_nao_pode_gerir_fornecedores(client, cliente_headers):
    resp = client.get("/fornecedores", headers=cliente_headers)
    assert resp.status_code == 403