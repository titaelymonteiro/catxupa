"""Testes da exportacao de dados para CSV."""
from conftest import criar_medicamento


def test_exportar_medicamentos_csv(client, admin_headers):
    criar_medicamento(client, admin_headers, nome="ExportMed", preco=123.0, estoque=5)
    resp = client.get("/exportar/medicamentos", headers=admin_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "medicamentos.csv" in resp.headers.get("content-disposition", "")
    assert resp.content.startswith(b"\xef\xbb\xbf")  # BOM (para o Excel)
    assert ";" in resp.text  # separador ponto-e-virgula
    assert "ExportMed" in resp.text


def test_exportar_clientes_csv(client, admin_headers):
    client.post("/clientes", json={"nome": "ClienteExport", "telefone": "9", "email": "e@e.cv",
                                    "endereco": "Praia"}, headers=admin_headers)
    resp = client.get("/exportar/clientes", headers=admin_headers)
    assert resp.status_code == 200
    assert "ClienteExport" in resp.text


def test_exportar_fornecedores_csv(client, admin_headers):
    client.post("/fornecedores", json={"nome": "FornExport", "nif": "1", "telefone": "9",
                                        "email": "f@f.cv", "endereco": "Praia"}, headers=admin_headers)
    resp = client.get("/exportar/fornecedores", headers=admin_headers)
    assert resp.status_code == 200
    assert "FornExport" in resp.text


def test_exportar_vendas_e_so_admin(client, admin_headers, funcionario_headers):
    assert client.get("/exportar/vendas", headers=admin_headers).status_code == 200
    assert client.get("/exportar/vendas", headers=funcionario_headers).status_code == 403


def test_funcionario_pode_exportar_medicamentos(client, funcionario_headers):
    resp = client.get("/exportar/medicamentos", headers=funcionario_headers)
    assert resp.status_code == 200


def test_cliente_nao_exporta(client, cliente_headers):
    assert client.get("/exportar/medicamentos", headers=cliente_headers).status_code == 403