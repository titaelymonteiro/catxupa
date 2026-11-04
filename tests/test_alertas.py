"""Testes dos alertas automaticos de stock baixo e validade."""
from datetime import date, timedelta
from conftest import criar_medicamento


def test_lista_alertas_stock_baixo(client, admin_headers):
    criar_medicamento(client, admin_headers, nome="AlertaStock", preco=100.0, estoque=3)
    alertas = client.get("/alertas", headers=admin_headers).json()
    nomes = [m["nome"] for m in alertas["stock_baixo"]]
    assert "AlertaStock" in nomes


def test_lista_alertas_validade_proxima(client, admin_headers):
    validade = (date.today() + timedelta(days=10)).isoformat()
    criar_medicamento(client, admin_headers, nome="AlertaValidade", estoque=50, validade=validade)
    alertas = client.get("/alertas", headers=admin_headers).json()
    nomes = [m["nome"] for m in alertas["validade_proxima"]]
    assert "AlertaValidade" in nomes


def test_lista_alertas_expirados(client, admin_headers):
    criar_medicamento(client, admin_headers, nome="AlertaExpirado", estoque=50, validade="2020-01-01")
    alertas = client.get("/alertas", headers=admin_headers).json()
    nomes = [m["nome"] for m in alertas["expirados"]]
    assert "AlertaExpirado" in nomes


def test_verificar_gera_notificacoes(client, admin_headers):
    criar_medicamento(client, admin_headers, nome="NotifStock", preco=100.0, estoque=2)
    resp = client.post("/alertas/verificar", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["novos"] >= 1

    notifs = client.get("/notificacoes", headers=admin_headers).json()
    assert any("NotifStock" in n["mensagem"] for n in notifs)
    assert any(n["tipo"] == "stock_baixo" for n in notifs)


def test_verificar_nao_duplica_alertas(client, admin_headers):
    criar_medicamento(client, admin_headers, nome="SemDuplicar", preco=100.0, estoque=1)
    client.post("/alertas/verificar", headers=admin_headers)
    segundo = client.post("/alertas/verificar", headers=admin_headers).json()["novos"]
    assert segundo == 0


def test_cliente_nao_acede_alertas(client, admin_headers, cliente_headers):
    resp = client.get("/alertas", headers=cliente_headers)
    assert resp.status_code == 403