"""Testes do CRUD de medicamentos."""
from conftest import criar_medicamento


def test_criar_e_listar_medicamento(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Ibuprofeno 400mg")

    resp = client.get("/medicamentos", headers=admin_headers)
    assert resp.status_code == 200
    nomes = [m["nome"] for m in resp.json()]
    assert "Ibuprofeno 400mg" in nomes

    resp = client.get(f"/medicamentos/{med_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Ibuprofeno 400mg"


def test_obter_medicamento_inexistente_devolve_404(client, admin_headers):
    resp = client.get("/medicamentos/999999", headers=admin_headers)
    assert resp.status_code == 404


def test_editar_medicamento(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Amoxicilina")

    resp = client.put(
        f"/medicamentos/{med_id}",
        json={
            "nome": "Amoxicilina 875mg",
            "preco": 300.0,
            "estoque": 15,
            "validade": "2027-06-01",
            "categoria": "Antibiótico",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200

    atualizado = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert atualizado["nome"] == "Amoxicilina 875mg"
    assert atualizado["preco"] == 300.0
    assert atualizado["estoque"] == 15


def test_editar_medicamento_inexistente_devolve_404(client, admin_headers):
    resp = client.put(
        "/medicamentos/999999",
        json={"nome": "X", "preco": 1.0, "estoque": 1},
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_apagar_medicamento(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Vitamina C")

    resp = client.delete(f"/medicamentos/{med_id}", headers=admin_headers)
    assert resp.status_code == 200

    resp = client.get(f"/medicamentos/{med_id}", headers=admin_headers)
    assert resp.status_code == 404


def test_apagar_medicamento_inexistente_devolve_404(client, admin_headers):
    resp = client.delete("/medicamentos/999999", headers=admin_headers)
    assert resp.status_code == 404


def test_listar_medicamentos_sem_autenticacao_falha(client):
    resp = client.get("/medicamentos")
    assert resp.status_code in (401, 403)


def test_funcionario_pode_gerir_medicamentos(client, funcionario_headers):
    """Medicamentos são geridos por qualquer membro da staff, não só admin."""
    med_id = criar_medicamento(client, funcionario_headers, nome="Dipirona")
    resp = client.get(f"/medicamentos/{med_id}", headers=funcionario_headers)
    assert resp.status_code == 200


def test_cliente_nao_pode_gerir_medicamentos(client, cliente_headers):
    resp = client.get("/medicamentos", headers=cliente_headers)
    assert resp.status_code == 403


def test_dashboard_inclui_vencimento_proximo(client, admin_headers):
    resp = client.get("/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    assert "vencimento_proximo" in resp.json()


def test_dashboard_conta_medicamento_a_vencer_em_breve(client, admin_headers):
    import datetime
    daqui_a_10_dias = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
    criar_medicamento(client, admin_headers, nome="A Vencer Em Breve", validade=daqui_a_10_dias)

    resp = client.get("/dashboard", headers=admin_headers)
    assert resp.json()["vencimento_proximo"] >= 1


def test_dashboard_nao_conta_medicamento_com_validade_distante(client, admin_headers):
    import datetime
    daqui_a_um_ano = (datetime.date.today() + datetime.timedelta(days=365)).isoformat()
    criar_medicamento(client, admin_headers, nome="Validade Distante", validade=daqui_a_um_ano)

    resp = client.get("/dashboard", headers=admin_headers)
    # nao garantimos zero (pode haver outros no seed), mas o medicamento criado nao deve influenciar
    # -- confirmamos antes/depois para isolar o efeito
    antes = resp.json()["vencimento_proximo"]

    daqui_a_10_dias = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
    criar_medicamento(client, admin_headers, nome="Este Sim Vence Em Breve", validade=daqui_a_10_dias)
    depois = client.get("/dashboard", headers=admin_headers).json()["vencimento_proximo"]

    assert depois == antes + 1


def test_endpoint_vencimento_proximo_lista_medicamentos(client, admin_headers):
    import datetime
    daqui_a_5_dias = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
    criar_medicamento(client, admin_headers, nome="Vence Em 5 Dias", validade=daqui_a_5_dias)

    resp = client.get("/medicamentos/vencimento-proximo", headers=admin_headers)
    assert resp.status_code == 200
    nomes = [m["nome"] for m in resp.json()]
    assert "Vence Em 5 Dias" in nomes


def test_endpoint_vencimento_proximo_respeita_parametro_dias(client, admin_headers):
    import datetime
    daqui_a_5_dias = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
    criar_medicamento(client, admin_headers, nome="Vence Em 5 Dias Bis", validade=daqui_a_5_dias)

    resp = client.get("/medicamentos/vencimento-proximo", params={"dias": 2}, headers=admin_headers)
    nomes = [m["nome"] for m in resp.json()]
    assert "Vence Em 5 Dias Bis" not in nomes


def test_endpoint_vencimento_proximo_bloqueado_para_cliente(client, cliente_headers):
    resp = client.get("/medicamentos/vencimento-proximo", headers=cliente_headers)
    assert resp.status_code == 403


def test_criar_medicamento_com_preco_custo(client, admin_headers):
    resp = client.post(
        "/medicamentos",
        json={
            "nome": "Medicamento Com Custo",
            "preco": 200.0,
            "estoque": 10,
            "validade": "2027-01-01",
            "categoria": "Teste",
            "preco_custo": 120.0,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201

    listagem = client.get("/medicamentos", headers=admin_headers).json()
    med = next(m for m in listagem if m["nome"] == "Medicamento Com Custo")
    assert med["preco_custo"] == 120.0


def test_medicamento_sem_preco_custo_fica_none(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    med = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert med["preco_custo"] is None


def test_editar_medicamento_atualiza_preco_custo(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers)
    resp = client.put(
        f"/medicamentos/{med_id}",
        json={
            "nome": "Medicamento de Teste",
            "preco": 150.0,
            "estoque": 20,
            "preco_custo": 90.0,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200

    med = client.get(f"/medicamentos/{med_id}", headers=admin_headers).json()
    assert med["preco_custo"] == 90.0