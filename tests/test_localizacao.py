"""Testes da localizacao: coordenadas de clientes/fornecedores e morada de
entrega nos pedidos online."""
from conftest import criar_medicamento


def test_cliente_guarda_coordenadas(client, admin_headers):
    client.post("/clientes", json={
        "nome": "ClienteGeo", "telefone": "9", "email": "g@g.cv",
        "endereco": "Achada", "latitude": 14.921, "longitude": -23.509
    }, headers=admin_headers)
    c = next(x for x in client.get("/clientes", headers=admin_headers).json()
             if x["nome"] == "ClienteGeo")
    assert c["latitude"] == 14.921
    assert c["longitude"] == -23.509


def test_fornecedor_guarda_coordenadas(client, admin_headers):
    client.post("/fornecedores", json={
        "nome": "FornGeo", "nif": "1", "telefone": "9", "email": "f@f.cv",
        "endereco": "Praia", "latitude": 14.9, "longitude": -23.5
    }, headers=admin_headers)
    f = next(x for x in client.get("/fornecedores", headers=admin_headers).json()
             if x["nome"] == "FornGeo")
    assert f["latitude"] == 14.9
    assert f["longitude"] == -23.5


def test_editar_cliente_atualiza_coordenadas(client, admin_headers):
    client.post("/clientes", json={"nome": "GeoEdit", "telefone": "9", "email": "ge@g.cv",
                                    "endereco": "A", "latitude": 14.0, "longitude": -23.0},
                headers=admin_headers)
    cid = next(x["id"] for x in client.get("/clientes", headers=admin_headers).json()
               if x["nome"] == "GeoEdit")
    client.put(f"/clientes/{cid}", json={"nome": "GeoEdit", "telefone": "9", "email": "ge@g.cv",
                                          "endereco": "A", "latitude": 15.0, "longitude": -24.0},
               headers=admin_headers)
    c = next(x for x in client.get("/clientes", headers=admin_headers).json() if x["id"] == cid)
    assert c["latitude"] == 15.0
    assert c["longitude"] == -24.0


def test_pedido_guarda_morada_entrega(client, admin_headers, cliente_headers):
    med_id = criar_medicamento(client, admin_headers, nome="MedEntrega", preco=100.0, estoque=10)
    resp = client.post("/pedidos", json={
        "itens": [{"medicamento_id": med_id, "quantidade": 2}],
        "morada_entrega": "Achada Santo Antonio, casa azul",
        "entrega_lat": 14.92, "entrega_lng": -23.51,
    }, headers=cliente_headers)
    assert resp.status_code == 201, resp.text
    pedido_id = resp.json()["pedido_id"]

    detalhe = client.get(f"/pedidos/{pedido_id}", headers=admin_headers).json()
    assert detalhe["morada_entrega"] == "Achada Santo Antonio, casa azul"
    assert detalhe["entrega_lat"] == 14.92
    assert detalhe["entrega_lng"] == -23.51