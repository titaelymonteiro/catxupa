"""Testes do CRUD de clientes."""


def _criar_cliente(client, admin_headers, **overrides):
    dados = {
        "nome": "Maria Silva",
        "telefone": "9991234",
        "email": "maria@example.com",
        "endereco": "Praia, Cabo Verde",
    }
    dados.update(overrides)
    resp = client.post("/clientes", json=dados, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_criar_e_listar_cliente(client, admin_headers):
    cliente_id = _criar_cliente(client, admin_headers)

    resp = client.get("/clientes", headers=admin_headers)
    assert resp.status_code == 200
    assert any(c["id"] == cliente_id for c in resp.json())


def test_editar_cliente(client, admin_headers):
    cliente_id = _criar_cliente(client, admin_headers, nome="Ana Costa")

    resp = client.put(
        f"/clientes/{cliente_id}",
        json={
            "nome": "Ana Costa Silva",
            "telefone": "9998765",
            "email": "ana@example.com",
            "endereco": "Mindelo, Cabo Verde",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200

    atualizado = client.get(f"/clientes/{cliente_id}", headers=admin_headers).json()
    assert atualizado["nome"] == "Ana Costa Silva"


def test_apagar_cliente(client, admin_headers):
    cliente_id = _criar_cliente(client, admin_headers)

    resp = client.delete(f"/clientes/{cliente_id}", headers=admin_headers)
    assert resp.status_code == 200

    resp = client.get(f"/clientes/{cliente_id}", headers=admin_headers)
    assert resp.status_code == 404


def test_historico_de_cliente_sem_compras_e_vazio(client, admin_headers):
    cliente_id = _criar_cliente(client, admin_headers)

    resp = client.get(f"/clientes/{cliente_id}/historico", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_historico_de_cliente_inexistente_devolve_404(client, admin_headers):
    resp = client.get("/clientes/999999/historico", headers=admin_headers)
    assert resp.status_code == 404